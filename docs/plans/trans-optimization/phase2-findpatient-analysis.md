# Phase 2 — `POST /trans/findPatient` 呼叫圖與優化計劃

- 日期：2026-09-14
- 分析對象：`LIS-transformer` `origin/main` @ `2d991af`（detached worktree `~/src/LIS-transformer-fp`，唯讀）
- 入口：`src/trans/trans-patient-search.controller.ts:215-381`（`findPatient`）→ `src/trans/getPatient.service.ts:369-1166`（`returnPatient`）
- Datadog 基線（7d）：p95 2.8 s、p50 1.0 s、29k calls/week
- 最高原則同 PLAN.md：**功能零改變**。每項變更都要能證明回應 JSON 與副作用相同。

## 0. 與「代表性 slow trace」事實的對照（先講差異）

任務描述的 trace 事實有三點與 current main **不符**，先記錄，避免後面照著錯的地圖修：

| 任務給的事實 | current main 實況 | 證據 |
|---|---|---|
| 14 個 lis-core gRPC，含 `ListSamples` / `GetCustomer` / `listCustomerPatients` | `returnPatient` 路徑**沒有** `ListSamples`、`GetCustomer`、`ListCustomerPatients`。`ListSamples` 只在同檔另一個 endpoint `sampleIssue()`（`getPatient.service.ts:6205`）。主查詢是 `InitialPatientPageHome`（`:806`） | grep 全檔；prod trace `6aa4aa9b000000002675c8ffe5311574`（2026-09-12，2.03 s）trans 側對 lis-core 的 gRPC 共 9 個：Stage A 5 個 + `GetSampleReceiveRecords` ×3 + `GetSampleTests` ×1 |
| trans 對自己打 `POST /utility/GetSampleInfo` | **不存在**於 findPatient 路徑。`src/` 裡除了 utility controller/service/dto 沒有任何檔案引用 `GetSampleInfo`；`git log -S"GetSampleInfo" -- src/trans src/setting` 為空（該字串從未出現在這兩個目錄）。Datadog：7 天內 `service:lis-trans-deployment span.kind:client @http.url:*GetSampleInfo*` = 0 筆；24 h 內 `POST /utility/GetSampleInfo` server span = 0 筆 | 見 §4。最可能的解釋：舊 trace 是 VP-17324 之前 calendar 走 HTTP（`va_events` URL，`getPatient.service.ts:5650-5653` 註解）的殘影，或 FE 另發的兄弟請求 |
| 只有 2 個 `Promise.all`、3 個 for-loop | `returnPatient` 本體確實 2 個 `Promise.all`（`:804`、`:955`）與 3 個 for（`:410`、`:651`、`:990`）；但它呼叫的 7 個 helper 內還有 10+ 個 `Promise.all` | §1 |

以下全部以 current main 為準。

## 1. Call graph（執行順序、是否在迴圈內、依賴）

符號：`[A]`=lis-core v7 gRPC（`microserviceOptions`，package `lis`，env `CORE_RPC_STAGE`，`trans.grpc.options.ts:6-38`；30 s timeout + 5 次 retry on UNAVAILABLE/UNKNOWN）、`[I]`=issue-system gRPC（package `issue`，`ISSUE_RPC`）、`[S]`=shipping gRPC（`SHIPPING_RPC`）、`[T]`=testresult gRPC（`TEST_RESULT_RPC`）、`[R]`=Redis、`[P]`=Prisma（trans 自己的 DB）、`[H]`=HTTP。

> `utilizedSampleService`（`:150-155`）在 prod = `sampleService`（lis-core v7）；非 prod = coresamplev2 `SampleService`（`CORE_SAMPLE_V2_RPC`）。以下 sample RPC 在 prod 一律算 `[A]`。

### 1.1 Controller（`trans-patient-search.controller.ts`）

| # | 行 | 呼叫 | 迴圈 | 依賴 | 失敗語意 |
|---|---|---|---|---|---|
| C0 | 215 | `CustomJwtAuthGuard`：JWT 驗簽（`auth/custom-jwt-auth.guard.ts`，secret 從 env，無 I/O） | – | – | 401 |
| C1 | 234 | `transService.getNavigatorPer` → `[A] InternalUserService.checkCustomerNavigator`（`trans.service.ts:16383`） | – | 只在 `role == 'navigator'` | 錯誤→回傳 `{internal_call_code:500}`，controller 只比對 `'denied'`，所以錯誤=放行 |
| C2 | 251 | `returnPatient(...)` | – | C1 | 見 1.2 |
| C3 | 342-375 | 對每個 `patient.Order[]` 有 TNP 類 issue 的 order：`transService.getTNPResult`（`trans.service.ts:20842`） | 巢狀 `Promise.all`，patients × orders（每 patient ≤5 orders，core 端 cap） | C2 的 `order.issue`（經 getWarning 過濾後） | 個別 try/catch 吞掉，保留原 issue |
| C3a | – | `getPatientTest`（`trans.service.ts:659`）：`[R] LRANGE lis_frontend_service_getPatientTest_{patient_id}`（TTL 500 s），miss→`[T] TestResultGrpcService.getPatientTestsResult`（`proxy.service.ts:139`） | 每個 TNP order | – | 錯誤→回 `{data: []}` 類空值 |
| C3b | – | `retryGetProductTestMaphttp`（`:1304`）→ `getProductTestMaphttp`（`:7993`）：`[R] GET`（EX 500）miss→`[H] POST process.env.GET_ORDER_details_CARLOS`（billing）；**最多 4 次重試，backoff 500/1000/2000 ms = 最多 3.5 s 純 sleep** | 每個 TNP order | – | 4 次皆失敗 throw `OrderDetailsUnavailableError` → getTNPResult 回 503 → controller 吞掉 |
| C3c | – | `getFullTestMapping`（`:18362`）：`[R] GET lis_full_test_mapping_{accession_id}`（EX 500）miss→`[H] GET process.env.full_test_mapping + accession_id` | 每個 TNP order | C3b | 同上 |

C3 在 prod 觸發機率低：`getWarning` 在 prod 會把 `'TNP'`、`'TNP Blood-Non-Blood'` 從 `order.issue` 移掉（`:5777-5800`、`:5715`），只剩 `'TNP Sample Type'` 會進 C3。但一旦觸發，C3b 的 backoff 是 p99 尾巴的候選。

### 1.2 `returnPatient`（`getPatient.service.ts:369-1166`）

| # | 行 | 呼叫 | 迴圈 | 依賴 | 失敗語意 |
|---|---|---|---|---|---|
| A0 | 694 | `settingyool.createMetadataForCoresampleV2` → `getOAuthToken()`（`setting/tool.ts:409-437`, `:103-200`）：快路徑純記憶體；token 到期/預取時 `[R] SET lis_frontend_service_oauth_fetch_lock EX 120 NX` + `[H] POST oauth_url` | – | – | 失敗→空 Bearer，不 throw |
| **A** | **804-943** | **`Promise.all` 5 個 `[A]`**：`PatientService.InitialPatientPageHome`（:806）、`PatientService.ListCustomerPatientsCount`（:876）、`CustomerService.IsNewCustomer`（:914）、`SettingService.GetSettingByCustomerClinic`（:922）、`SettingService.GetClinicSetting`（:931） | – | 只依賴 request 參數 | 任一 reject → 外層 catch（:1142）→ `{internal_call_code:500}` → controller 回 200 `{total_count:0, patients:[], newCustomer:'false'}`（controller:328-333） |
| B | 955-964 | `filterPatientlite` ×N patients → `cleanOrderlitenew` ×orders → `getOrderStatus`（:3457，純 CPU；:2977 的 `await` 是假的） | `Promise.all` over patients；內部 `Promise.all` over orders；再 for over samples（**`Order[]` 是一 row per sample**） | A | throw → 外層 catch → 500 語意如上 |
| B1 | 990-1021 | 分 `patient_with_order` / `patient_without_order`；依 `patient_service_date` 排序 | for | B | – |
| **C** | **1023** | `getEstimateTimev3`（:1453-1720） | – | B（需要 `Order[].sample_id`、`report_status`） | 內部 catch（:1699）→ **回傳輸入原引用**（etd 等欄位可能已部分寫入） |
| C1 | 1483-1484 | `createMetadataForCoresampleV2` ×2（同參數重複呼叫） | – | – | 不 throw |
| C2 | 1494-1496 | `[A] SampleService.GetSampleReceiveRecords({sample_id})` | **`sample_ids.map`（N = report_status=='report_pending' 的 sample 數）**，並行 | B | 任一 reject → 整個 C 進 catch |
| C3 | 1500-1506 | `getSamplesEventsInProcess` → `calendarEventService.getSamplesEvents`（`calendar/event/event.service.ts:748`）→ `getOneSampleEvents` ×accession（:775）：`[P] sample_event.findMany` **每個 accession 一次**；每個 event `convertToEventObject`（:941）→ `getCliniciansMapping`（:895）`[R] GET`（8 h TTL）miss→`[P] clinicians.findMany` | 並行 over accession_ids（所有 order） | B | `getSamplesEventsInProcess` catch → `undefined` → 後面 `getEventsByAccesionids[...]` 會 TypeError → 整個 C 進 catch |
| C4 | 1509-1510 | `edrOverrideService.loadActiveOverridesForCalc(sample_ids)`（`edr-override.service.ts:502`）：`[P] sample_edr_override.findMany`、`[P] sample_test_edr_override.findMany`、`[R] GET edr_override:rules:test_type:v1` / `test_id:v1`（TTL 60 s；miss→`[P]` + `SETEX`） | – | B | reject → 整個 C 進 catch |
| **C5** | **1571-1578** | **`[A] SampleService.GetSampleTests({sample_ids})`** — 在 C2/C3/C4 **之後**才發，但它只依賴 `sample_ids` | – | 只依賴 B | reject → C 進 catch |
| C6 | 1609-1650 | 每個 sampleTest：`getMaxTurnaroundDaysPerTestTypeWithAddon`（純 CPU）→ `calculateEDRWithAddon`（:2273）→ `mapOfTubeTypeAndSampleTypev2`（:5513）：`[R] GET lis_frontend_service_mapOfTubeTypeAndSampleTypev2_{tube_type}`（TTL 86400，daily cron 續命 :5573）miss→`[A] SampleService.GetTubeSampleTypeInfoViaTubeTypeSymbol` | `Promise.all` over sampleTests；內部 over unique tube types | C2, C5 | `mapOfTubeTypeAndSampleTypev2` catch → `undefined`；計算端 `mapv2[0]` 會 throw → C 進 catch |
| **D** | **1030** | `getIssue`（:3914-4025） | – | **只依賴 B 的 `sample_id`**（不依賴 C） | catch（:4016）→ 回傳輸入原引用 |
| D1 | 3924 | `createMetadataForCoresampleV2` | – | – | – |
| D2 | 3954-3959 | `[I] IssueService.BatchGetIssuesByObjectIds({foreign_object_id:11, object_ids})` — 已是 batch | – | B | reject → D 進 catch |
| D3 | 3991-4002 | `filterOrderLevelIssue`（:5461）：`[R] LRANGE lis_frontend_service_filterOrderLevelIssue`（TTL 86400）miss→`[P] issue_display.findMany({level:'Order'})` | **每個 order 一次**（同一把 key 重複讀 M 次；trace 可見 4 個並行 LRANGE） | D2 | 內部 catch → `undefined` → `order.issue = undefined` |
| **E** | **1039** | `getPatientIssue`（:4141-4207） | – | **只依賴 B 的 `patient_ny_waive_form_issue_status`**（不依賴 C、D） | catch → 回傳輸入原引用 |
| E1 | 4153 | `createMetadataForCoresampleV2` | – | – | – |
| E2 | 4168-4172 | `get_issue_id(12, patient_id)`（:4210）→ `[I] IssueService.QueryForeignLink`（:4237）→ `[I] IssueService.GetIssues`（:4258） | **每個有 NY waive issue 的 patient 2 個 RPC（N+1，且兩個串行）**，patient 間並行 | B | `get_issue_id` catch → `undefined` → `:4178 .object_id` TypeError → E 進 catch |
| E3 | 4181 | `filterPatientLevelIssue`（:5209）：`[R] LRANGE lis_frontend_service_filterPatientLevelIssue`（TTL 86400）miss→`[P] issue_display.findMany({level:'Patient'})` | **每個 patient 一次** | E2 | – |
| **F** | **1042** | `getFedExTrackingNumbers`（:4025-4131） | – | **D**（找 `order.issue` 含 `'FedEx Warning'`） | 每 order 的 catch 設空陣列；外層 catch 回輸入 |
| F1 | 4056 | `proxyService.getKitStatus` → `[S] ShippingService.GetKitStatusBySampleId`（`proxy.service.ts:86-107`；內含另一次 `createMetadataForCoresampleV2`） | `Promise.all` over 有 FedEx Warning 的 orders | D | 個別降級 |
| **G** | **1048** | `getWarning`（:6073-6110）→ `processTNPWarningData` / `processTNPWarningDataRedrawed` / `processMissingOptionalTubeIssue` / `processTestDiscontinuedIssue` | – | **A**（settings→`auto_redraw`、`joinBetaProgram`）+ **D**（`order.issue`） | 全程 catch |
| G' | 5773-6019 | `processTNPWarningDataRedrawed`：prod 分支 :5775-5800 直接 `return`；非 prod 分支 :5993-6017 也是純 map。:5802-5992 那段有 `[H] POST process.env.GET_ORDER_CARLOS` 的 code 是 **dead code**（在 `return` 之後） | – | – | **實際上所有環境皆零 I/O** |
| H | 1059 | `removeEmptySampleOrder`（:2516，純 CPU） | – | – | – |
| H1 | 1068 | `applyAmendedUnreadOnlyFilter`（純 CPU） | – | A（filter 展開） | – |
| H2 | 1127 | `seedPatientMoneyKeys`（:325，純 CPU；VP-18197 已移除 accounting HTTP） | – | – | catch 吞 |

### 1.3 prod trace 時間軸（`6aa4aa9b…`，2.03 s，供估算用）

```
55.431 ┬ Stage A  Promise.all  ───────────────── 56.098  (InitialPatientPageHome 667 ms 佔滿；Count 208, IsNew 155, Settings 14/67)
56.102 ├ C2 GetSampleReceiveRecords ×3 並行 45 ms │ C3 calendar prisma │ C4 edr rules cache miss → prisma + SETEX (56.161 / 56.257)
56.280 ├ C5 GetSampleTests ────────── 56.721  (442 ms，串在 C2-C4 後面)
56.722 ├ C6 tube type Redis GET ×8（含重複：SST/TES/EDTA 各 2 次）
56.724 ├ D2 BatchGetIssuesByObjectIds ────────── 57.214  (491 ms)
57.215 ├ D3 LRANGE filterOrderLevelIssue ×4
57.216 ├ E1 OAuth lock SET（token 預取）
57.216 ├ F1 GetKitStatusBySampleId ────── 57.453  (237 ms)
57.458 ┴ 回應
```

Stage A 之後的 B～H 全部串行，合計 ≈ 1.36 s；其中彼此無資料依賴的 C（≈0.62 s）、D+F（≈0.73 s）、E（本例 0）若並行，可壓到 ≈0.73 s。

## 2. Parallelization（可合併的 await 群）

### P1（主力）：C ∥ (D → F) ∥ E，再做 G、H

`returnPatient:1023-1046` 現在是：

```
C getEstimateTimev3 → D getIssue → E getPatientIssue → F getFedExTrackingNumbers → G getWarning → H removeEmptySampleOrder
```

資料依賴（§1.2）：C、D、E 三者都只讀 B 的輸出、寫**不同欄位**（C：`order.etd/etd_override/active_event_id`；D：`order.issue`；E：`patient.issue`）。F 只讀 D 寫的 `order.issue`。G 讀 D 的 `order.issue` 與 A 的 settings。改成：

```ts
await Promise.all([
  this.getEstimateTimev3(patient_with_order, ...),                       // C
  this.getIssue(patient_with_order, ...).then((r) =>                     // D → F
    this.getFedExTrackingNumbers(r, tracking_id, authorization)),
  this.getPatientIssue(patient_with_order, ...),                         // E
]);
patient_with_order = await this.getWarning(patient_with_order, ...);    // G
patient_with_order = await this.removeEmptySampleOrder(patient_with_order, ...); // H
```

**原錯誤語意**：C、D、E、F 各自內部 catch 並回傳輸入原引用（`:1699`、`:4016`、`:4200`、`:4127`），從不 reject；所以 `Promise.all` 在這裡等價於 `allSettled`，不會改變「一個 helper 掛掉只降級該欄位、不影響其他欄位」的行為。唯一要注意的是四者共用同一組物件引用（`getIssue` 等回傳的就是傳入的陣列，`:1030-1040` 的三個變數其實同一個物件），並行寫入不同欄位是安全的；但 D3 的 `order.issue = await filterOrderLevelIssue(...)` 與 G 讀 `order.issue` 之間必須維持先後（上面結構已保證）。

**getWarning 的第一行**（:6084-6088）`Order.map(async order => order['warning'] = [])` 沒有 await，實際是同步副作用；並行後仍在 D 之後執行，不變。

預期：本例省 ≈0.6 s（2.03→≈1.4 s）；p95 估 2.8→≈2.1 s。

### P2：`GetSampleTests` 併入 C 的第一波 `Promise.all`

`getEstimateTimev3:1571` 的 `GetSampleTests({sample_ids})` 只依賴 `sample_ids`，卻排在 C2/C3/C4 之後（本例晚 180 ms 才發，自身 442 ms）。搬進 `:1508` 的 `Promise.all`。

保留早退語意：`:1518` 與 `:1546` 兩個早退分支不再省掉這次 RPC（多打一次無害的讀 RPC，回應不變）；`sample_ids.length === 0` 時仍跳過（原本 `combinedResultsRaw` 為空會早退）。預期省 ≈0.15-0.2 s（C 從 0.62 → 0.44 s）。

### P3：`createMetadataForCoresampleV2` 一個 request 建一次

`:694`、`:1483`、`:1484`、`:3924`、`:4153`、`:5531-5532`、`proxy.service.ts:91` 各自重建。`mapOfTubeTypeAndSampleTypev2` 已支援 `prebuiltMeta` 參數。改成在 `returnPatient` 建一次往下傳。快路徑是純記憶體，latency 收益小；價值在減少 token 預取的競態（trace 中 `:57.216` 的 `SET oauth_fetch_lock`）。

## 3. N+1

| 位置 | 每項 RPC | 基數 | proto 裡有 batch 嗎 | 建議 |
|---|---|---|---|---|
| E2 `get_issue_id(12, patient_id)` `:4168-4172` → `QueryForeignLink` + `GetIssues` | 2 個 `[I]` 串行 / patient | 有 NY waive issue 的 patient 數（≤ perPage） | **有**：`IssueService.BatchGetIssuesByObjectIds(BatchGetIssuesByObjectIdsRequest{foreign_object_id, repeated object_ids})`（`protos/issue-system-protos/issue_service.proto:90`、`issue.proto:75-83`）。D2 已用同一 RPC 處理 `foreign_object_id: 11`（sample） | 改成一次 `BatchGetIssuesByObjectIds({foreign_object_id: 12, object_ids: patient_ids})`，沿用 `:3960-3985` 的 mapping（欄位與 `get_issue_id:4270-4310` 一致：`fk.resolution.is_resolved`、`fk.issue_type.name/description`）。**前提**：issue-system 對 `foreign_object_id=12` 的支援要在 staging 實測（不能假設）；**不改下游** |
| C2 `GetSampleReceiveRecords({sample_id})` `:1494-1496` | 1 個 `[A]` / pending sample，並行 | pending sample 數（本例 3；一頁最多 ≈ perPage×5） | **有**：`SampleService.GetSampleReceiveRecordsBatch(GetSampleReceiveRecordsRequestList{repeated sample_ids}) returns GetSampleReceiveRecordsResponseMap{repeated SampleReceiveBatchEntry{sample_id, repeated sample_details}}`（`protos/sample.proto:33,560-573`；coresamplev2 `sample_service.proto:38` 同名）。同檔 `:4824` 已在用 | 用 batch 取代，寫一個 adapter 把 `sample_receive_batch_entries[]` 轉回 `[{sample_receive_list}]` 陣列（下游 `:1538-1556` 依賴此形狀）。latency 收益小（本來就並行、45 ms），主要是 core 連線數與 retry 面積 |
| C3 calendar `getOneSampleEvents` `event.service.ts:775` | 1 個 `[P] findMany` / accession | 所有 order 數 | 不是 gRPC，是同 repo 的 Prisma；可改成一次 `findMany({where:{accession_id:{in}}})` 再 group | 可做，但要保留 `orderBy created_at desc` 與 `deleted_at` 的 `active_event_id` 選法（:788-794）。優先度低 |
| D3 / E3 `filterOrderLevelIssue` / `filterPatientLevelIssue` | 1 個 `[R] LRANGE` / order（/ patient） | orders（≤ perPage×5） | 不適用（同一把 key） | 一個 request 只讀一次：新增內部 `loadIssueDisplay(level)` 回傳 data，兩個 filter 函式接受已載入的 data。Redis ops 從 M 降到 1，latency 收益 ≈ 0 |
| C6 `mapOfTubeTypeAndSampleTypev2` | 1 個 `[R] GET` / unique tube type / sample | 本例 8 次（應為 4） | 不適用 | `tubeTypeCache` 現在存值不存 promise，`:1609` 並行的 sample 在第一個 resolve 前都 miss。改成 cache promise。收益 ≈ 幾 ms |
| C3 (controller) `getTNPResult` | 1×`[T]` + 1-4×`[H]` + 1×`[H]` / TNP order | 通常 0-2 | `getProductTestMaphttp` 本身接受 `sampleId[]`（`:1316` 傳 `[sampleId]`），可一次帶多個 | 先量：Datadog 查 `findPatient` trace 下 `GET_ORDER_details_CARLOS` 的 client span 頻率與 retry 次數再決定；backoff 上限 3.5 s 是 p99 候選但屬行為變更，Phase 2 不動 |

不存在 batch 的：`GetKitStatusBySampleId`（`protos/shipping.proto`，只有單筆）— F1 已並行，不再處理。

## 4. Self-HTTP call（`POST /utility/GetSampleInfo`）

- **current main 沒有這條呼叫**（證據見 §0）。`getPatient.service.ts` 內 `axios` 只出現在 `postRequest`（:5674-5713，`redis.get` + `axios.post` + `EX 50`），而 `postRequest` 在 `returnPatient` 路徑無呼叫者（`settingyool.postRequest` 只在 §1.2 G' 的 dead code）。
- 接收端（若日後有人想打）：`utility.controller.ts:712-735` `@Controller('utility') @Post('/GetSampleInfo')`，`CustomJwtAuthGuard` + `resolveIdsForHttpOptional(req.user, data, [], {optional:['user_id','internal_user_id']})` → `utilityService.getSampleInfo(sample_ids, is_all_tat, data.authorization, request_id, record_user_id, bearer)`（`utility.service.ts:1606`）→ `getPatientTransService.getEstimateTimev3Sample(...)`（`getPatient.service.ts:4349`）。回 `{sample_test_tat}`。
- **能否 in-process 直呼**：能。`getEstimateTimev3Sample` 就是 `GetPatientTransService` 自己的 method；`UtilityService` 也在 `TransModule.providers`（`trans.module.ts:173`）。HTTP 路徑多做的只有 JWT 驗簽（findPatient 已做過）與從 token 取 `user_id/internal_user_id`；**沒有**對 `sample_ids` 做 ownership 檢查，所以直呼不會跳過任何授權判斷。
- 結論：Phase 2 這裡**沒有可做的事**。若 Datadog 再出現 trans→trans 的 `GetSampleInfo` client span，要先確認 caller 是哪支 code（目前 repo 內找不到），不要憑舊 trace 動工。

## 5. Redis（路徑上既有快取）

| Key | 位置 | TTL | 備註 |
|---|---|---|---|
| `edr_override:rules:test_type:v1` / `edr_override:rules:test_id:v1` | `edr-override.service.ts:22-23,594-680` | 60 s（`EDR_OVERRIDE_CACHE_TTL_SECONDS`） | miss → Prisma + `SETEX`；本例 miss（+~110 ms） |
| `lis_frontend_service_mapOfTubeTypeAndSampleTypev2_{tube_type}` | `:5515-5570` | 86400 s；`@Cron('0 0 0 * * *')`（:5573）每日以 `tag='concurrent'` 強制刷新 | miss → `[A] GetTubeSampleTypeInfoViaTubeTypeSymbol` |
| `lis_frontend_service_filterOrderLevelIssue` / `..._filterPatientLevelIssue`（list） | `:5468-5480`、`:5216-5228` | 86400 s | miss → Prisma `issue_display` |
| `lis_frontend_service_oauth_fetch_lock` | `tool.ts:127-134` | 120 s NX | token 本體在記憶體（`this.token`） |
| calendar clinicians mapping | `event.service.ts:895-935` | 8 h | 每個 event 讀一次 |
| `lis_frontend_service_getPatientTest_{patient_id}` | `trans.service.ts:661-681` | 500 s | 只在 C3（controller TNP 後處理） |
| `getProductTestMaphttp` key / `lis_full_test_mapping_{accession_id}` | `trans.service.ts:7993+`、`:18362+` | 500 s | 同上 |

**沒有快取**的：Stage A 五個 RPC（settings、isNewCustomer 每次都打）、receive records、sample tests、issues、kit status。Stage A 的 `GetClinicSetting`/`GetSettingByCustomerClinic`/`IsNewCustomer` 可快取但會引入 staleness（設定改了要等 TTL），屬**行為變更**，Phase 2 不做；若要做，另開 PR 並與 setting 寫入端的 cache bust 一起設計。

## 6. Risk table

| 變更 | 回應 / 副作用可能的差異 | 驗證 |
|---|---|---|
| P1 C∥(D→F)∥E | (1) 同物件並行寫不同欄位：只要沒人寫同一欄位就無差；需逐欄位核對（C：`etd`、`etd_override`、`active_event_id`；D：`issue`；E：patient `issue`；F：三個 `*_tracking_numbers`）。(2) 錯誤降級順序：原本 C 掛掉 → D 仍以 C 寫入一半的物件為輸入；並行後相同（都是原引用）。(3) 日誌順序改變（`lis_front_logger` 的 error log 時間交錯），非功能。(4) getWarning 讀 `order.issue` 必須在 D3 完成後：結構上保證 | 單元：新 spec 用 fake helper 驗證四個 stage 寫入欄位互斥、任一 stage reject/回傳 undefined 時最終物件與串行版一致。Shadow：staging 對同一批 request 跑舊/新兩版，`JSON.stringify` 全回應 diff（排序敏感欄位 `patients[].Order[]` 已由 `orderInfo.sort` 固定）。Datadog：`resource_name:"POST /trans/findPatient"` p50/p95 前後 7 天比較 |
| P2 GetSampleTests 提前 | `:1518`/`:1546` 早退分支多打一次讀 RPC；`sample_ids=[]` 時仍不打。回應不變 | spec：pending sample 為 0 / receive list 全空 兩個 case 驗證 `GetSampleTests` 呼叫次數與輸出 |
| P3 metadata 建一次 | `x-request-id`、`user-id` 相同；token 取用時間點提前幾百 ms，過期邊界理論上可能拿到不同 token，但 core 不驗 exp（`tool.ts:143-150` 註解） | spec：mock `createMetadataForCoresampleV2` 計數 = 1 |
| N+1 → `BatchGetIssuesByObjectIds(12)` | (1) issue-system 是否支援 fk 12 — 未知，需 staging 實測；(2) `get_issue_id` 的 `QueryForeignLink` 找的是 `fk.object_id`，batch 的語意需相同；(3) 失敗語意：原本任一 patient 的 `get_issue_id` 回 `undefined` → E 整個降級；batch 版單一 RPC 失敗 → 同樣整個降級，一致 | staging 抓 20 個有 NY waive 的 patient 對兩種取法 diff `patient.issue`；shadow diff 全回應 |
| N+1 → `GetSampleReceiveRecordsBatch` | 回應形狀不同要 adapter；`internal_received_time` / `received_time` 欄位是否都在 `sample_details` 內要對 proto（`sample.proto:587` `ReceiveSampleResponse`）確認；順序不保證 → `:1538` 的 `result[0].sample_id` 比對仍成立（同一 entry 內同 sample） | spec 對 adapter；shadow diff `Order[].etd` |
| Redis 表載入一次 | 無 | spec 計數 |
| tube type cache 存 promise | 無；miss 時 `undefined` 的傳播與現在相同 | 既有 `getPatient.service.edr.spec.ts:145-238` 已覆蓋 cache 行為，補一個並行 case |
| （順帶發現，不在 perf PR 內）`this.send_issue_order_type` / `this.send_order_test_flag`（`:410-418`）是 **instance 欄位、每個 request 只 push 不清空** → 跨 request 污染 filter（某 request 選過 `order_covid-tt` 後，之後所有 request 的 OR bucket 都帶它）且無上限成長 | 正確性 bug；`appendFilterValues` 的 cap 50 與去重讓影響有界，但值會殘留 | 另開 ticket，改成 local 變數；驗證方式：兩個 request 序列 spec |

## 7. 建議的 PR 順序（每個都可獨立上）

| 步 | 內容 | 檔案 | 預期效果（以 2.03 s trace 估） | 風險 |
|---|---|---|---|---|
| 1 | 補測試基礎：為 `returnPatient` 加一個以 fake gRPC/Redis/Prisma 為底的 golden-response spec（目前 `src/trans/*.spec.ts` 沒有任何檔案引用 `returnPatient`），固定一組輸入 → 完整 JSON 快照 | `src/trans/getPatient.service.returnPatient.spec.ts`（新） | 0 ms；是後面每一步的安全網 | 無 |
| 2 | **P1**：C ∥ (D→F) ∥ E | `getPatient.service.ts:1023-1046` | −0.6 s（本例）；p95 估 2.8 → ~2.1 s | 中（見 §6） |
| 3 | **P2**：`GetSampleTests` 併入第一波 | `getPatient.service.ts:1494-1578` | C 內 −0.15~0.2 s；在步 2 之後 C 仍是最長分支之一，所以會直接反映到總時長 | 低 |
| 4 | Redis 表一次載入 + tube type promise cache + 修 `send_*` instance 欄位（獨立 commit） | `:3991-4002`、`:4181`、`:5461`、`:5209`、`:2320-2340`、`:410-418` | 幾 ms；Redis ops −(M−1)×2 | 低 |
| 5 | **P3** metadata 建一次 | `:694`、`:1483-1484`、`:3924`、`:4153` + 傳參 | 幾 ms | 低 |
| 6 | E2 → `BatchGetIssuesByObjectIds(12)`（先 staging 實測 issue-system 支援） | `:4141-4207` | 只在有 NY waive patient 時有感：每個 patient 省 1 個串行 RPC（~15-20 ms/RPC × 2 → 1 個 batch） | 中（下游語意） |
| 7 | C2 → `GetSampleReceiveRecordsBatch` + adapter | `:1494-1496`、`:1538-1556` | latency ≈ 0；core RPC 數 −(N−1) | 低-中 |
| 8 | （量測後決定）controller TNP 後處理：Datadog 統計 `findPatient` 下 `GET_ORDER_details_CARLOS` client span 的次數/耗時，若 p99 尾巴確實在這裡，另案討論 backoff 上限 | `trans-patient-search.controller.ts:342-375`、`trans.service.ts:1304-1330` | p99 專屬 | 行為變更，Phase 2 不做 |

**不建議在 Phase 2 做**：快取 Stage A 的 settings/isNewCustomer（staleness）；動 core 端 `InitialPatientPageHome`（667 ms，其中 580 ms 是 core v7 轉打 coresamples-v2 並上傳 shadow-diff 到 blob — 屬 core 團隊範圍）。

## 附：查證方法備忘

- 程式碼：`grep -rn GetSampleInfo src`；`git log -S"GetSampleInfo" -- src/trans src/setting`；`awk` 取 `returnPatient` 範圍內的 `for`/`await`。
- Datadog（vibrant MCP，us3）：`search_datadog_spans` `service:lis-trans* resource_name:*findPatient* @duration:>2000000000`（3d，63 筆）→ `trace_id:6aa4aa9b000000002675c8ffe5311574 service:lis-trans-deployment -operation_name:express.middleware`（39 spans，時間排序）；`service:lis-trans-deployment span.kind:client @http.url:*GetSampleInfo*`（7d，0 筆）。
- 注意：Datadog span 上的 `git.commit.sha aafc62c` 標成 `lis-backend-coresamples` repo，不是 trans 的 commit，不能用來對 trans 版本。
