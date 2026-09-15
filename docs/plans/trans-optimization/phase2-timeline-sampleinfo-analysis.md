# Phase 2 — `POST /trans/getTimeLine` 與 gRPC `TransService/GetSampleInfo` 呼叫圖與優化計劃

- 日期：2026-09-14
- 分析對象：`LIS-transformer` `origin/main` @ `2716968`（detached worktree `~/src/LIS-transformer-tl`，唯讀；HEAD = PR #769 merge）
- 交叉引用：LIS-Sample `~/src/LIS-Sample`（唯讀，只為解析 `getKitStatusV2` 的目的地）、prod ConfigMap dump `appendix-b-k8s-inventory.md`、Datadog indexed spans（7d，`retainedby: diversity_sampling`，計數是抽樣值，只看比例與分位）
- 最高原則同 PLAN.md：**功能零改變**。每項變更都要能證明回應 JSON 與副作用相同。

符號：`[A]`=lis-core v7 gRPC（`microserviceOptions`，`CORE_RPC_STAGE` = `lis-core-grpc-service.default:30113`，`trans.grpc.options.ts:6-9`）、`[I]`=issue-system gRPC（`ISSUE_RPC`）、`[R]`=Redis、`[P]`=Prisma（trans 自己的 DB）、`[H]`=HTTP（axios）、`[H-pub]`=HTTP 走公網 ingress `api.vibrant-wellness.com`。
`utilizedSampleService`（`getPatient.service.ts:150-155`）在 prod = lis-core v7 `SampleService`；非 prod = coresamplev2。以下 sample RPC 在 prod 一律算 `[A]`。

---

## A. `POST /trans/getTimeLine`

### A.0 先修正一個前提

PLAN 懷疑 `getKitStatusV2` 指回 trans v1 自己的 `/trans/patientTestKitInfo`。**不是直接指回，但結果更糟——是經 LIS-Sample 繞一圈回來**：

| 證據 | 內容 |
|---|---|
| ConfigMap `default/lis-trans-config`（appendix-b:41） | `getKitStatusV2 -> https://api.vibrant-wellness.com/v1/lis/samples`（公網） |
| Datadog client span（7d，311 筆抽樣） | `GET https://api.vibrant-wellness.com/v1/lis/samples/patients/v2/kits`，p50 **1.39 s**，p95 **2.74 s**。`peer.service` 被 Datadog 標成 `lis-base-report`——**是誤標**，phase0 §4.6 表中「`http.request GET lis-base-report ×2 1,800 ms`」其實就是這支 kits 呼叫（同一 `resourcehash a509a3c69ad1028d`） |
| LIS-Sample ingress（`yamls/lis-sample-ingress.yml:35`） | `/v1/lis/samples(/|$)(.*)` → lis-sample-service |
| LIS-Sample `patients.controller.ts:190-197` → `patients.service.ts:1761` `getKitStatusV2` → `:1765` 先呼叫 `getKitStatus`（v1） | v1 內部（`:1635-1697`）：shipping gRPC `getSampleId`（含 retry）→ `Promise.all[listSamplePatientGrpc, getSample_coreSampleService]` → `getPortalJwt`（4 個 gRPC/HTTP 串行：`listSamplesInfoInBatch`、`getSampleRelevantInfoGrpc`、`retrieveOrderV2InfoBySampleId`、`transferLISTokenToPortalGrpc`）→ **`axios.get(LIS_TRANS_HTTP_URL + 'trans/patientTestKitInfo?patient_id=&accession_id=')`（`:1676-1681`，打回 trans v1）** → `enrichTubeInfoWithImages` |
| trans v1 `GET /trans/patientTestKitInfo` server span（7d，752 筆） | p50 0.41 s、p95 1.18 s；內部 `listSamplesAccesionID`[A] + `cleanOrder_patientTestKitInfo`（`trans.service.ts:11656`）每 sample `Promise.all[getTestOrderBillInfo(lis-order orderV2), getTubeInfoV2([A] getSampleTubesCount + getSampleReceiveRecords + mapOfTubeTypeAndSampleTypev2)]` + `getKitInfoReal`（shipping） |
| LIS-Sample server span `GET /patients/v2/kits`（7d，532 筆） | p50 1.33 s、**p95 5.51 s** |

`getTimeLine` 對這整串只用一個 bit：`timeline_body.has_report = Boolean(kitStatusResponse?.data?.tube_info && !isEmpty(...))`（`trans.service.ts:23782-23785`）。而 `tube_info` 的來源就是 trans 自己 `getTubeInfoV2` 的回傳（`trans.service.ts:11715` `tube_info: clend[1]`），LIS-Sample 只做兩件事：(1) 只有 `Order[0].kit_status` truthy 時才帶回 `tube_info`（`patients.service.ts:1690-1704`），(2) `enrichTubeInfoWithImages` 加圖 URL（空陣列原樣回傳，`:1525-1526`）。

### A.1 Controller（`trans-notifications.controller.ts:2197-2246`）

| # | 行 | 呼叫 | 條件 | 失敗語意 |
|---|---|---|---|---|
| C0 | 2197 | `CustomJwtAuthGuard` | – | 401 |
| C1 | 2220-2233 | `checkSampleCustomer`（`trans.service.ts:18820`）：串行 `listSample`（`:494`，`[R] GET` EX 60 → miss `[A] ListSamples`）→ `getPatient`（`:13005`，`[R] GET` EX 120 → miss `[A] GetPatient`）→ `listClinicCustomersByClinicID`（`:13121`，`[R] LRANGE` **TTL 5 s** → miss `[A] ClinicService.listClinicCustomersByClinicId`） | 只在 `req.user.internal_user_id` 為空（portal/clinic 使用者）；loop 固定 1 次 | 任何錯 → false → 403 |
| C2 | 2236 | `transService.getTimeLine(...)` | – | 回 `internal_call_code` 當 HTTP status |

C1 三步互相獨立於結果只有 `patient_id` 這一條依賴（`getPatient` 需要 `listSample` 的 `patient_id`；`listClinicCustomersByClinicID` 不需要）。在 2026-09-15 trace `6aa88b7700000000382ef6cee638db50` 中對應 `ListSamples` 82 ms + `GetPatient` 227 ms（clinic customers 為 Redis hit）。

### A.2 `TransService.getTimeLine`（`trans.service.ts:23676-24274`）

| # | 行 | 呼叫 | 平行? | 依賴 | 失敗語意 |
|---|---|---|---|---|---|
| T0 | 23731 | `await this.settingTool.serviceToken()`（`setting/tool.ts:248`）——寫在 `Promise.all([...])` **陣列字面值的第一個元素內** | **否**：陣列元素由左到右求值，這個 `await` 解析前，T2–T5 的 promise 根本還沒建立 | – | 快路徑純記憶體；token 過期/負快取時 `[R] SET NX` + `[H-pub] POST oauth`（10 s timeout）；失敗回 legacy `process.env.token`，不 throw |
| T1 | 23729-23735 | `[H] POST GET_ORDER_CARLOS`（lis-order in-cluster `/orderTest/orderV2`，body `{sampleIdList:[sample_id], limit:2000}`） | 是（Promise.all） | T0 | `postRequest` 不 throw，回 `{transbadstatus:500}` → 後續 `testOrderBillInfo` 為 undefined → `:23819` `testOrderBillInfo.chargeMethod` **throw** → 整支 500 `'Failed'`（spec `trans.service.getTimeLine.spec.ts:255` 已鎖定此行為） |
| T2 | 23736-23744 | `[P] time_line.findMany({where:{sample_id}, orderBy:[create_date desc, id desc]})` | 是 | – | throw → 整支 500 |
| T3 | 23745-23750 | `[H] GET getOrderItemsAndHistory + sample_id`（lis-order in-cluster） | 是 | – | `{transbadstatus:500}` → `:23794` 回 500 `'Failed to fetch order items and history'` |
| T4 | 23750 | `patientInfo(...)`（`:16416-16571`）：`createMetadataForCoresampleV2` → `[I] get_issue_id`（`getPatient.service.ts:4210`：`queryForeignLink` + 條件 `getIssues`）→ `[R] LRANGE lis_frontend_service_patientInfo_{patient_id}`（**TTL 10 s**，`:16442`）→ miss：`getPatient`（`[R] GET lis_frontend_service_patientv2_{id}` EX 120 → `[A] GetPatient`）+ `filterPatient_lite`（純轉換）→ `[R] RPUSH/EXPIRE`；hit/miss 皆再 `filterPatientLevelIssue`（`[R] LRANGE ..._filterPatientLevelIssue` TTL 86400 → miss `[P] issue_display.findMany`） | 是 | – | 內部 catch 回 `{internal_call_code:500,error}`，呼叫端只讀 `patientInfo?.patient_email` → 變 null，不影響狀態碼 |
| T5 | 23751-23756 | `[H-pub] GET getKitStatusV2 + accession_id` = **A.0 那一整圈** | 是 | – | `{transbadstatus:500}` → `.data` undefined → `has_report=false` |
| T6 | 23763-23778 | `[H-pub] GET getinvoice + orderIdStr`（`api.vibrant-wellness.com/v1/accounting/charge/invoice`，accounting） | **否**，在 Promise.all 之後串行 | T1 的 `orderIdStr` | try/catch + `getRequest` 不 throw；7d 抽樣 **464 筆中 246 筆 HTTP 400（53%）**，400 時 p50 0.12 s |
| T7 | 23841-24170 | 純 CPU：`time_line.forEach` switch 分類、付款去重 | – | T2 | – |
| T8 | ~24206-24228 | `[H-pub] GET CHARGE_INFO_URL=...&charge_type=testorder`（`api.vibrant-wellness.com/v1/lis/accounting/charge/invoice`），前面再 `await serviceToken()` | **否**，串行 | 只在 T6 失敗或 `transbadstatus` 時 | try/catch；7d 抽樣 246 筆全為 400（與 T6 的 400 一一對應） |
| T9 | ~24232-24245 | PPL 時從 `time_line` 找 `patientPayLaterOrderPlace` 解析 email | – | T2 | 純 CPU |

**代表 trace**（`6aa88b7700000000382ef6cee638db50`，2026-09-15 00:04，4,119 ms，browser 直打）：Promise.all 內 kits 3,285 ms（其他：orderV2 837、GetPatient 227、orderItemsAndHistory 218、ListSamples 82、QueryForeignLink 37、Redis ×8 各 <1 ms）→ 串行 invoice 229 ms（400）→ 串行 chargeInfo 238 ms（400）。**關鍵路徑 = T5 + T6 + T8 ≈ 3.75 s**；把 T5 拿掉後關鍵路徑變成 T1（0.84 s）+ T6（0.23 s）+ T8（0.24 s）≈ 1.3 s。

Redis keys / TTL 一覽：`lis_frontend_service_patientInfo_{patient_id}`（10 s，list）、`lis_frontend_service_patientv2_{patient_id}`（120 s）、`lis_frontend_service_filterPatientLevelIssue`（86400 s）、`lis_frontend_service_ListSamples_*`（60 s，C1）、`lis_frontend_service_oauth_fetch_lock`（120 s NX）。`time_line` 沒有快取。

### A.3 可平行但目前串行（保留錯誤語意）

1. **T0 擋住整個 Promise.all**：`serviceToken()` 應先 `await` 到變數或改成 `serviceToken().then(tok => postRequest(...))` 放進陣列，讓 T2–T5 同時起跑。錯誤語意不變（`serviceToken` 從不 throw）。正常快路徑省 <1 ms；token 輪替窗口（每 ~1 h 一次、120 s 內）省最多 10 s。
2. **T6/T8 可掛在 T1 後面而不必等 T5**：把 `sharePayment.then(r => invoice(r[sample_id]?.orderIdStr)).then(fallback)` 當第 6 個 promise 放進 Promise.all，try/catch 邏輯照搬。`invoiceResponse` 只被 `:23773`（credit_applied）與 `:24206` 之後（payment_status）讀取，皆在 Promise.all 之後 → 輸出不變。省 T6+T8 全部（p50 0.25 s、p95 0.5 s）——**這是不碰 kits 也能拿到的最低風險收益**。
3. **C1 三步**：`listClinicCustomersByClinicID` 不依賴 `listSample`，可與 `listSample→getPatient` 平行；省 ~50–200 ms（只影響 portal 使用者）。

### A.4 N+1 / 自呼叫 / 公網回繞

- **自呼叫（間接）**：T5 → 公網 → LIS-Sample → 公網或 in-cluster（`LIS_TRANS_HTTP_URL`）→ trans v1 `/trans/patientTestKitInfo` → core ×3 + lis-order + shipping。trans 只需要其中 `getTubeInfoV2` 的空/非空。
- **公網回繞**：T5、T6、T8 三支全走 `api.vibrant-wellness.com`。in-cluster 對應：accounting `ACCOUNTING_BASE_URL -> lis-accounting-service.bkkeeping.svc.cluster.local:8084/v2/accounting`（同 ConfigMap 已有）；lis-sample `lis-sample-service.sample.svc.cluster.local:16300`（只出現在 transv2 ConfigMap `get_pns_kit_status`，trans v1 ConfigMap 沒有）。
- 沒有迴圈型 N+1（`Sample_ids` loop 固定 1 筆）。`time_line.findMany` 一次撈全部事件再在記憶體分類，量不大。
- `time_line` 的 Prisma model（`prisma/schema.prisma:109-115`）**沒有 `@@index([sample_id])`**；prod DB 是否有索引未能驗證（trans DB 不在我可查的 `lisportalprod` host；trace 也沒有 Prisma span）。需 `EXPLAIN` 確認。

### A.5 風險表

| 變更 | 行為風險 | 說明 |
|---|---|---|
| T5 改為 in-process `getTubeInfoV2`（`:8987`） | **中** | 輸出 bit 相同的條件：LIS-Sample 只在 `Order[0].kit_status` truthy 時回 `tube_info`；trans 自己算會在「有 tube 但 kit_status 為 null（如 `getTestOrderBillInfo` 為空）」時多給 true。另外 LIS-Sample 任何一步失敗（portal JWT、shipping getSampleId）目前都會讓 `has_report=false`，改後這些假陰性消失——是修正還是行為改變，需 Leo/PM 定調。若要 bit-exact，改呼叫 `patientTestKitInfo(...)`（`:12910`，含 Redis 120 s cache）並套用同一個 `kit_status` 條件 |
| T5 只改 URL 為 in-cluster lis-sample | 低 | 省一跳 ingress（<100 ms），LIS-Sample 仍會打回 trans；不值得單做 |
| A.3-1、A.3-2 | 低 | 純排程順序，錯誤處理搬進 `.then` 鏈；用現有 spec（`trans.service.getTimeLine.spec.ts` 8 個 case）+ 新增「invoice 失敗→fallback」與「sharePayment 失敗→500」順序驗證 |
| T6/T8 走 in-cluster accounting | 低-中 | `getinvoice` 與 `CHARGE_INFO_URL` 的完整路徑在 ConfigMap 被截斷，需先確認 `/v1/accounting/charge/invoice` 對到 `lis-accounting-service` 的哪個 base；且 53% 的 400 顯示這兩支對半數訂單本來就無效，先查 400 原因（`orderIdStr` 型別？非 PPL 訂單無 invoice？）再決定是否跳過 |
| 移除 `patientInfo` 內 issue 相關呼叫 | 低 | `getTimeLine` 只讀 `patient_email`；但 `patientInfo` 是共用 helper，不能改它本體，只能在 `getTimeLine` 改呼叫 `getPatient`+`filterPatient_lite`。非關鍵路徑，收益小，不建議這輪做 |

### A.6 PR-sized 步驤與估計

| 步 | 內容 | 預估 | 風險 |
|---|---|---|---|
| A-PR1 | A.3-1 + A.3-2（serviceToken 移出陣列；invoice/fallback 鏈掛進 Promise.all） | p50 −0.25 s、p95 −0.5 s（T6+T8 移出關鍵路徑） | 低 |
| A-PR2 | T5 改 in-process（建議先用 `patientTestKitInfo` + 同條件求 bit-exact，之後再考慮直接 `getTubeInfoV2`） | p50 2.2 → ~1.0 s、p95 3.4 → ~1.6 s（關鍵路徑改由 T1 orderV2 0.8 s 主導） | 中（A.5 第一列） |
| A-PR3 | C1 平行化；`time_line` 索引驗證與補索引（若缺） | portal 使用者 −0.1–0.2 s；索引影響待量 | 低 |
| A-PR4 | 查 invoice 400 根因，決定是否條件跳過 T6/T8 | 影響 A-PR1 後剩餘的 0.25 s | 需資料 |

---

## B. gRPC `TransService/GetSampleInfo`

### B.1 入口與呼叫者

- gRPC：`utility.controller.ts:693-711` `@GrpcMethod('TransService','GetSampleInfo')` → `utilityService.getSampleInfo(sample_ids, is_all_tat, data.authorization, request_id, record_user_id, authorization)`（`utility.service.ts:1606-1661`）→ `getPatientTransService.getEstimateTimev3Sample`（`getPatient.service.ts:4349-4583`）。
- REST twin：`utility.controller.ts:713-738` `POST /utility/GetSampleInfo`（`CustomJwtAuthGuard`）呼叫同一個 service method。7d 抽樣：REST 1,014 筆 p95 **0.47 s**；gRPC 250 筆 p95 **3.09 s**。差異來自 `sample_ids` 基數。
- gRPC 呼叫者（7d client spans）：`lis-sample-deployment` 240 筆 p95 0.35 s（`LIS-Sample/src/tests/tests.service.ts:439-476`，**每次 1 個 sample_id**，`is_all_tat:false`，retry）；`lis-test-connect-deployment`（results-grpc）19 筆 p95 **4.09 s**（`check-pending.service.ts:160-176`，**每 chunk 最多 100 個 sample_id**，`is_all_tat:false`，結果再存自己的 Redis）。LIS-Shipping 有 `TransService` client（`issues.utility.ts:41`）但沒有呼叫 `GetSampleInfo`。
- proto：`protos/trans-service-protos/trans_service.proto:8-9`——`GetSampleInfo` 與 **`GetSampleInfoV2`**（同 request/response）；V2 → `getSampleInfoV2` → `getEstimateTimev4Sample`（`getPatient.service.ts:4800-5040`，2026-03-16 `cafb064` 加入）。**V2 在 prod 7d 內 0 筆呼叫。**

### B.2 `getEstimateTimev3Sample` 執行順序（N = `sample_ids.length`）

| # | 行 | 呼叫 | 平行? | 基數 | 失敗語意 |
|---|---|---|---|---|---|
| S0 | 4361-4364 | `createMetadataForCoresampleV2` ×2（`Promise.all`，兩個完全相同；prod 用第一個） | 是 | 2 | 不 throw（空 Bearer） |
| S1 | 4373-4388 | `Promise.all[ Promise.all(sample_ids.map(getSampleReceiveRecords)), getSampleTests({sample_ids}), edrOverrideService.loadActiveOverridesForCalc(sample_ids) ]` | 是 | **[A] GetSampleReceiveRecords ×N（N+1）** + [A] GetSampleTests ×1 + `[P] sample_edr_override / sample_test_edr_override findMany(in)` ×2 + `[R] GET edr_override:rules:test_type:v1 / test_id:v1`（TTL 60 s，miss → `[P] test_type_edr_rule / test_id_edr_rule`） | gRPC 任一 reject → 整支 catch → 回 `undefined` → `getSampleInfo` 回 `{sample_test_tat: undefined}` |
| S2 | 4393-4443 | 空結果 fallback（純 CPU） | – | – | – |
| S3 | 4448-4508 | `Promise.all(sampleTests.map(...))`：每 sample `getMaxTurnaroundDaysPerTestTypeWithAddon`（純 CPU，`:1754`）→ 內層 `for re_result` 線性掃描找同 sample（O(N²) 比對，N≤100 可忽略）→ `calculateEDRWithAddon`（`:2273`）：對 request 級 `tubeTypeCache` 沒有的 tube_type 做 `mapOfTubeTypeAndSampleTypev2`（`:5513`：`[R] GET lis_frontend_service_mapOfTubeTypeAndSampleTypev2_{tube_type}` TTL 86400 → miss `[A] GetTubeSampleTypeInfoViaTubeTypeSymbol`；有每日 cron 預熱 `:5595`） | 是 | Redis GET ×(distinct tube types)，通常全 hit | `calculateEDRWithAddon` 內 catch 回 `max_days:-1` |
| S4 | 4509-4563 | 組回傳；sample-level override 時 `await lis_front_logger.log_info`（winston，同步寫 log，非網路） | 串行 | ≤N | – |
| S5 | 4564-4566 | `is_all_tat` 時 `getTestTAT`（`:4594-4798`）：每 sample 再 `Promise.all(mapOfTubeTypeAndSampleTypev2)`（**沒有共用 S3 的 `tubeTypeCache`**，但 Redis 全 hit） | 每 sample 串行 | 兩個 prod caller 都傳 `false` | catch 只記 log |

**代表 trace**（`6aa7ccf90000000035de4c131f3bf9ba`，2026-09-14 10:31，3,461 ms，caller `lis-test-connect-deployment`，N = 20）：20 支 `GetSampleReceiveRecords` 平行，client 端各 127–158 ms（core 端 52–88 ms），牆鐘 ~160 ms；**`GetSampleTests` 3,439 ms（core 端 3,235 ms，內部 `MGET` ×1 + `SET` ×20 → 20 個 sample 全部 cache miss 後逐筆查 DB）**。core 端 `GetSampleTests` 7d p50 6 ms、p95 275 ms——單 sample 幾乎全 hit，多 sample miss 批次才拖到秒級。

**結論：gRPC 路徑的 p95 3 s 是 core `GetSampleTests` 在 results-grpc 的多 sample 批次上的 cache-miss 成本，不是 trans 的 N+1。** N+1 的成本是連線與 core 負載（100 支並發 unary），不是牆鐘時間。

### B.3 Batch RPC 是否存在

存在，而且 trans 已經在用：`protos/sample.proto:33` 與 `protos/coresamplev2/sample_service.proto:38` 都有 `GetSampleReceiveRecordsBatch(GetSampleReceiveRecordsRequestList{repeated string sample_ids}) returns (GetSampleReceiveRecordsResponseMap{repeated SampleReceiveBatchEntry})`；`getEstimateTimev4Sample:4824` 已呼叫。core 端 7d：`GetSampleReceiveRecordsBatch` 3,689 筆 p50 28 ms、p95 37 ms（vs 單筆 p50 39 ms、p95 97 ms）。

v3 → v4 的差異（parity 檢查清單）：(a) receive records 改 batch，並用 `receiveMap` 以 `result[0].sample_id` 索引（與 v3 線性比對等價）；(b) tube type 先全 request 預抓一次（v3 在 `calculateEDRWithAddon` 內邊算邊抓，兩者最終都是 Redis hit）；(c) v4 把 `prebuiltMeta` 傳 `undefined`（`:4953`）→ `mapOfTubeTypeAndSampleTypev2` miss 時自己再建 metadata（多 2 次 OAuth 快路徑）；(d) `is_all_tat` 用 `getTestTATv2`（`:5042`）而非 `getTestTAT`。現有 spec `getPatient.service.edr.spec.ts:1311`、`:2000` 覆蓋 v3；v4 需要對同一組 fixture 的 deep-equal 比對測試。

### B.4 風險表

| 變更 | 風險 | 說明 |
|---|---|---|
| `getSampleInfo` 改呼叫 `getEstimateTimev4Sample`（或把 v3 的 S1 換成 batch RPC） | 中 | 輸出應相同但 v4 從未上 prod；`SampleReceiveBatchEntry.sample_details` 與 `sample_receive_list` 欄位對應（`internal_received_time` fallback `received_time`）在 v4 已照搬。建議：先在 v3 內只換 S1（最小 diff），`is_all_tat` 分支不動 |
| 對 core `GetSampleTests` 多 sample miss 的 3 s | 不在 trans 範圍 | 屬 `LIS-backend-coreSamples`；trans 端唯一能做的是把 results-grpc 的 chunk 縮小（更多 RPC，不建議）或加 trans 側 per-sample TAT 快取（改變新鮮度語意，results-grpc 自己已有 Redis，不建議） |
| 拿掉 S0 重複的 `createMetadataForCoresampleV2` | 無 | 兩個回傳在 prod 只用一個 |
| S5 `getTestTAT` 共用 `tubeTypeCache` | 無 | prod caller 不傳 `is_all_tat:true`，收益為 0，順手改即可 |

### B.5 PR-sized 步驟與估計

| 步 | 內容 | 預估 | 風險 |
|---|---|---|---|
| B-PR1 | v3 的 S1 換 `getSampleReceiveRecordsBatch`（保留其餘 v3 邏輯）；刪重複 metadata | N=100 時牆鐘 −0.1–0.2 s（160 ms → ~40 ms）；core 端每 chunk 少 99 支 unary；**p95 幾乎不動**（被 GetSampleTests 主導） | 中（需 v3/v4 deep-equal spec） |
| B-PR2 | 量測：對 `GetSampleTests` 加 `sample_ids.length` 到 log/trace tag，把「N 與 core 耗時」的關係交給 core owner | 0 | 無 |
| B-PR3 | `GetSampleInfoV2` 若確定無人用，標 deprecated 或讓 V1 直接委派 v4，避免兩份 EDR 邏輯漂移（2026-05-14 `eb4a915` 的 override 已要同步改兩處） | 維護性 | 低 |

---

## C. 兩者共同的觀察

1. **公網回繞是 getTimeLine 的主因**（T5 一支 p50 1.4 s），且它繞回 trans 自己。PLAN Phase 1.3「公網回繞改 in-cluster」對 getTimeLine 的正確做法不是改 URL，而是**不要出去**（A-PR2）。
2. Datadog `peer.service` 對公網呼叫一律標 `lis-base-report`，phase0 各 trace 表中的「lis-base-report」需重新對 `http.url` 判讀。
3. `GetSampleInfo` gRPC 的慢是 core cache-miss 批次，trans 側 batch 化是「該做但不會改 p95」的事；預期值要先跟 Leo 對齊，避免 PR 上線後看不到指標變化被當成失敗。
4. 未驗證項：`time_line` prod 索引；`getinvoice`/`CHARGE_INFO_URL` 的完整路徑與 400 根因；LIS-Sample 側 `getKitStatusV2` 3–5 s 的內部分佈（該 trace 的 LIS-Sample span 沒有接進同一個 trace）。
