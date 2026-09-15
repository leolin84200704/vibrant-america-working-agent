# Phase 2 — `GET /trans/patientTestResultnewrange` 讀碼分析（trans v1, N+1 reference range）

- 分析對象：`~/src/LIS-transformer-nr`（detached worktree, origin/main @ `2716968`, 2026-09-14）。唯讀，未改 repo。
- Datadog（7d）：p50 2.3 s / p95 6.1 s / 7,335 calls / error 1.87%。
- 本文另外抓了兩條 prod trace 對照碼路徑：`6aa88a94…d5891c`（5.6 s，101 child spans）與 `6aa88679…4386e`（7.5 s，337 child spans）。
- 所有 file:line 都在 `src/trans/` 下；`T` = `trans.service.ts`，`C` = `trans-patient-info.controller.ts`。

## 0. 先講結論（跟前提不完全一樣）

1. 365 次 `GetPatientDetailedReferenceRangeInOut` **確實是 N+1，但已經是 `Promise.all` 併發**（T:1430-1442），不是 serial。7.5 s trace 裡 ~300 次全部在同一秒發出、1.5 s 內收完；代價是 core 端被打爆——單次 RPC 從 80 ms（25 併發時）膨脹到 0.4–1.5 s（300 併發時）。改 batch 省的是這 ~1.5 s 加上 core 的負載，不是 6 s。
2. 兩條 slow trace 裡**最大的單一 span 都是 `GET …/base-report-service/result/testHierarchyForReports`（3.1 s / 4.5 s）**，對應 `getFullTestMapping`（T:18362），走公網 `api.vibrant-wellness.com` HTTPS，Redis 500 s cache miss 時才打。它只依賴 `accession_id`（request 一進來就知道），卻被放在 reference-range fan-out 之後 serial await（T:1428 → T:1602）。把它提前併發，是比 batch 更便宜、更大的一刀。
3. 1.87% error 幾乎不是 gRPC 錯誤造成的：fan-out 內任何錯誤都被 catch 成空 rangeinfo（degrade），不會變 500。500 來自 `patientTestResultnewrange` 最前段的三個 fast-fail（見 §1.4），Datadog 上的 500 span 都在 60–100 ms 內結束，與此一致。

## 1. Call graph（執行順序）

### 1.1 Controller（C:682-759）
| 步 | 呼叫 | 條件 / 迴圈 | 錯誤語意 |
|---|---|---|---|
| a | `getNavigatorPer` → gRPC `InternalUserService.checkCustomerNavigator`（T:16374-16395） | 只在 `role == 'navigator'` | catch 回 `{internal_call_code:500}` 物件 ≠ `'denied'` → **放行**（fail-open） |
| b | `ownsPatient` → `checkPatientCustomer`（T:18876-18916）= `getPatient`（Redis `lis_frontend_service_patientv2_{pid}` 120 s → gRPC `PatientService.GetPatient`）+ `listClinicCustomersByClinicID`（Redis lrange 5 s → gRPC `ClinicService.listClinicCustomersByClinicId`） | `is_trusted_internal` 跳過 | catch 回 undefined → 403 |
| c | `transService.patientTestResultnewrange(...)`（T:13413） | — | `internal_call_code == 500` → HTTP 500 `Internal Error`（C:751-757） |

### 1.2 Service 主體 `patientTestResultnewrange`（T:13413-13516）
1. Redis `LRANGE lis_frontend_service_patientTestResultnewrange_{pid}_{acc}`（T:13438）。**TTL 1 秒**（T:13481），實務上等於沒有 cache，只擋 double-click。
2. `getPatient`（T:13005-13050）——與 b 同 key，通常 cache hit。取 `patient_order`，線性掃 `samples[0].accession_id == accession_id` 找 order（T:13444-13450）。
3. 找不到 → `return {internal_call_code:500, error:'No order found'}`（T:13451-13456）。
4. `filterPatient_split(..., 'patientTestResultnewrange')`（T:10928）→ `cleanOrder_patientTestResultnewrange`（T:11886）。
5. `RPUSH` + `EXPIRE 1`，回 `{Order: result.Order}`（T:13479-13487）。
6. 外層 catch：log + Sentry + `return {internal_call_code:500}`（T:13492-13515）。

### 1.3 `cleanOrder_patientTestResultnewrange`（T:11886-11970）—— 迴圈 `order.samples`（實務上 1 個，因為 order 是用 accession 找到的）
每個 sample **serial**：
- `get_issue_id(11, sample_id)`（getPatient.service.ts:4210）→ gRPC `IssueService.QueryForeignLink` + `GetIssues`（trace 裡 420 ms）→ 算 `order_billing_issue_status`（T:11912-11924）。
- `getTestReportResultnewrange(...)`（T:1345）→ 塞進 `orderinfo.test_related`。
- catch 只 log（且 `String(e)` 的 `e` 是 `import e from 'express'`，T:16——log 內容是 express function 的字串，不是錯誤），不 rethrow → `test_related` 缺、response 仍 200。

### 1.4 `getTestReportResultnewrange`（T:1345-2233）—— 熱點所在
| 步 | 呼叫 | 並行性 | 資料依賴 | 錯誤語意 |
|---|---|---|---|---|
| A | `Promise.all([getPatientTest, retryGetProductTestMaphttp, getTestOrderBillInfo])`（T:1364-1368） | 3 併發 | 只要 ids | `getPatientTest` rethrow（T:701）；`retryGetProductTestMaphttp` 4 次 retry 後 throw `OrderDetailsUnavailableError`（T:1304-1332, Sentry 68057）；任一 reject → 整個函式進 catch，回 **undefined** → `test_related: undefined`，HTTP 仍 200 |
| A1 | `getPatientTest`：Redis lrange `…_getPatientTest_{pid}` 500 s → gRPC `TestResultGrpcService.GetPatientTestsResult`（T:659-704） | | | |
| A2 | `retryGetProductTestMaphttp` → `getProductTestMaphttp`：Redis get `…_getProductTestMaphttp_{sid}` 500 s → HTTP POST `GET_ORDER_details_CARLOS`（lis-order `/orderTest/orderTestDetails`）（T:7993-8040） | | | |
| A3 | `getTestOrderBillInfo`：Redis lrange `…_getTestOrderBillInfo_{sid}` **10 s** → HTTP POST `GET_ORDER_CARLOS`（lis-order `/orderTest/orderV2`，trace 803 ms）；bundle item 會再打 A2（T:7221-7300, 7372） | | | |
| B | 組 `mini_PatientTestsResult`：該 sample 的所有結果 + **同 test_id 在病人其他 sample 的歷史結果**（T:1386-1400）。這就是 N 的來源：測項數 × 歷史 sample 數 → 300+。 | CPU | | |
| C | `Promise.all(mini.map(clenaTestResultnewrange))`（T:1430-1442）→ 每筆 `getPatientReferenceRangeInOutnewrange`（T:4195）→ `getDetailRangeInfo`（T:5168）→ **gRPC `ReferenceRangeService.GetPatientDetailedReferenceRangeInOut`**（T:5191） | N 併發 | 需 A1 | 見 §2 |
| D | `contentList` 空 → `connectFromProductToTestnewrange_for_null_detail`（T:1461, 未 await） | | | |
| E | `orderDetailsMapping` + `getFullTestMapping(Map, …, accession_id)`（T:1598-1602）：Redis get `lis_full_test_mapping_{acc}` 500 s → **HTTPS GET `process.env.full_test_mapping + accession_id`**（trace 3.1 s / 4.5 s） | **serial，在 C 之後** | 只需 `accession_id`（`Map` 只用來過濾結果） | catch 回 undefined → 下一行 `full_mapping.map` TypeError → 進外層 catch → `test_related` undefined |
| F | `Promise.all(full_mapping.map(connectFromProductToTestnewrange))`（T:1605-1620）——純 CPU，除了 tnp 分支每筆 `getTnpCode`（Redis 48 h cache, T:3656） | | 需 C 的 `patient_Data` | |
| G | `in_progress` 非空 → `inProgressTestEDR`（T:17021）：gRPC `SampleService.getSampleReceiveRecords` ∥ `TestService.getTest`，再 `mapOfTubeTypeAndSampleTypev2` 併發 | 內部已併發 | 需 F | catch 只 log，etd 缺 |
| H | `compleated` 非空 → **serial** 三個 HTTP：`axios.get(url_packageOldAndNewNameMapping)`（T:1938）、`axios.get(Get_product_report_map+'aa')`（T:1944）、`GetSpecificReports` → old report service 寫檔到本機再 `readJsonFromFile`/`deleteFile`（T:1955-1972） | serial | 只需 ids | 前兩個 throw → 外層 catch → undefined；第三個回 `{internal_call_code:500}` 則跳過 report 對照 |
| I | MTHFR 7184 拆分（純 CPU），return `{compleated, tnp, in_progress, report_final}` | | | |

### 1.5 1.87% error 的來源（code 可見）
- **`No order found`**（T:13451）：accession 不在該病人 `patient_order[*].samples[0]` → 500。注意只比 `samples[0]`；多 sample order 的第二支 accession 也會 500。
- **`TypeError: Cannot read properties of undefined (reading 'length')`**（Sentry 68047，410 events）：`returnRPC.patient_order` 為 undefined（GetPatient 沒回 order、或 Redis 快取了無 order 的 patient）→ `Order.length`（T:13444）→ catch → 500。
- 垃圾 query：Datadog 上看到 `patient_id=&accession_id=portal.vibrant-wellness.com` 的 500。
- Datadog 7d 的 500 span 全部 60–100 ms 結束 → 都是上面這類 fast-fail，**不是** gRPC 超時。fan-out 內的 gRPC 錯誤在 `getDetailRangeInfo` catch 被吞成空 rangeinfo（T:5865-5903），永遠不會變 500。
- 註：`sentry-event-filter.ts:22` 已把 controller 的 wrapper 500 當 duplicate 丟掉，只留 service 層原因。

## 2. N+1 細節

### 2.1 迴圈與 per-item request
- 迴圈：T:1430-1442 `Promise.all(mini_PatientTestsResult.map(p => clenaTestResultnewrange(p, …)))`。
- 進入 RPC 的條件（T:2903-2913）：`latestTestValue` 非空、`approvedStatus === true`、且（數值 ≥0 或 == -999999）或非數值字串。
- 每筆 request（T:5191-5199）：
  ```ts
  { test_id: String(p.testId), sample_id: String(p.sampleId), result_value: '0' }   // result_value 永遠是 '0'
  ```
  失敗會**原地重試 3 次**（T:5190-5222 巢狀 try），且 `exception_test`（NutriPro）非空時走 HTTP `NutriProZ`（T:5228-5246）再 fallback 同一個 gRPC。
- 回傳 `DetailedResultRespondInOutList { In, All, Error }`，程式只用 `All`（T:5223），`Error` 欄位被忽略；`All` 空會在 `ranges[0].precision_digit`（T:5311）TypeError → catch → 回 T:5876-5902 的空物件（`tag:''`, `zone` 全空）。
- 每筆額外 `await createMetadataForCoresampleV2` 兩次（T:4208 與 T:5185；OAuth token 有 in-memory cache，tool.ts:45-55，通常 0 網路）。

### 2.2 Batch RPC 形狀（protos/reference-range.proto）
```
rpc GetPatientDetailedReferenceRangeInOutBatch(PatientInfos) returns (DetailedResultRespondInOutLists)   // :20
message PatientInfos { repeated PatientInfo patientInfos = 1; }                                        // :58
message PatientInfo  { string test_id = 1; string sample_id = 2; string result_value = 3; }             // :245
message DetailedResultRespondInOutLists { repeated DetailedResultRespondInOutListBatch result = 1; }   // :162
message DetailedResultRespondInOutListBatch { repeated DetailedResultRespond In = 1; repeated DetailedResultRespond All = 2;
                                              string sample_id = 3; string test_id = 4; }              // :165
```
欄位對映：
| 單筆 | Batch | 備註 |
|---|---|---|
| request `PatientInfo{test_id,sample_id,result_value}` | `PatientInfos.patientInfos[i]` 同型別 | 直接 push；`result_value` 維持 `'0'` 才與現況等價 |
| response `.All` | `result[k].All` | 同 `DetailedResultRespond` 型別，`getDetailRangeInfo` 的計算段（T:5297-5862）可原樣重用 |
| response `.In` | `result[k].In` | 現況未使用 |
| response `.Error` | **無**——batch item 沒有 Error 欄位 | 失敗 item 大概只會缺席或 `All` 為空；需向 core 確認 |
| — | `result[k].sample_id/test_id` | **join key**；不可假設順序 |

- proto 已由 `lis_main.proto:15` import，`this.client`（`CORE_RPC_STAGE`, T:230-232）動態載入，batch 方法可直接呼叫；`wrapGrpcService` 的 camelCase proxy 對 `getPatientDetailedReferenceRangeInOutBatch` 有效。
- **trans 已有 batch 實作但是死碼**：`getPatientReferenceRangenewInOutbatch`（T:6052-6465）呼叫該 batch RPC 並用 `(sample_id, test_id)` 雙迴圈 join（T:6072-6081）；上游 `clenaTestResultnewrangebatch`（T:2961）→ `getTestReportResultnewrangebatch`（T:2237）沒有任何 caller。它的計算邏輯是舊版（沒有 `NO_REFERENCE_RANGE` 早退、沒有 `calculateOutput` 邊界修正、沒有 reportable range clamp），**不能直接拿來用**，只能借 RPC 呼叫與 join 的骨架。
- `getTestReportResultnewrangeV2`（T:13744）/`getDetailRangeInfoV2`（T:14257）走 `labTestReferenceRangeService`（lab-test service），是另一個 endpoint，不在本文範圍。

### 2.3 錯誤語意變化
| 現況（N 筆單發） | Batch |
|---|---|
| 單筆 gRPC 失敗 → 重試 3 次 → 仍失敗 → 該筆 rangeinfo 空物件，其他筆不受影響 | 整個 batch 失敗 → **全部**筆空 rangeinfo。要保留現況需：batch 失敗 → fallback 到現有 per-item 路徑（或分 chunk 重送） |
| `All` 空 → 該筆空物件 | `result` 缺該 key 或 `All` 空 → 該筆空物件（join miss 視同單筆失敗）|
| NutriPro exception_test 走 HTTP | 這些 test_id 先從 batch 名單剔除，維持原路徑 |
| dedupe：同 (sample_id,test_id) 重複出現時各打一次 | batch 前用 Map 去重，結果共用；輸出不變 |

## 3. 其他可併行的 serial await
| # | 位置 | 現況 | 建議 | 依賴 / 輸出 | 錯誤語意 |
|---|---|---|---|---|---|
| P1 | E `getFullTestMapping`（T:1602） | 等 C 完才打，3–4.5 s | 在函式開頭與 A 的 `Promise.all` 同時 kick（promise 先存著，到 E 再 await） | 只需 `accession_id`；輸出獨立 | 提前 reject 要 `.catch` 包住，到 E 才 rethrow，維持「進外層 catch」 |
| P2 | H 三個 HTTP（T:1938/1944/1955） | serial ≈ 130 ms | `Promise.all` 三個 | 互不依賴 | 前兩個 reject 仍 throw；第三個回 500 物件不 throw——用 `allSettled` 或維持個別處理 |
| P3 | 1.3 `get_issue_id`（T:11901） vs `getTestReportResultnewrange` | serial 420 ms | 併發；`order_billing_issue_status` 只在 clena 內做遮罩（T:2929-2934） | 要先算 status 才能進 C；可改成 C 前 await（與 A 併發） | 不變 |
| P4 | Controller b `getPatient` 與 service 2 `getPatient` | 同 key 兩次，第二次 cache hit | 不動 | | |
| P5 | Redis `EXPIRE 1`（T:13481） | 幾乎無效的 cache | 不建議先動（影響資料新鮮度語意，需 Leo 決定） | | |

## 4. Redis 使用（本路徑）
| Key | TTL | 寫入點 |
|---|---|---|
| `lis_frontend_service_patientTestResultnewrange_{pid}_{acc}` | 1 s | T:13479-13481（list） |
| `lis_frontend_service_patientv2_{pid}` | 120 s | T:13026（string） |
| `lis_frontend_service_getPatientTest_{pid}` | 500 s | T:678-681（list） |
| `lis_frontend_service_getProductTestMaphttp_{sid}` | 500 s（僅 contentList 非空才寫） | T:8018 |
| `lis_frontend_service_getTestOrderBillInfo_{sid}` | 10 s | T:7292-7330 |
| `lis_full_test_mapping_{acc}` | 500 s | T:18373 |
| `lis_frontend_service_getTnpCode` | 172800 s | T:18476-18490 |
| `lis_frontend_service_listClinicCustomersByClinicID_{clinic}` | 5 s | T:13121-13160（list） |
| OAuth 鎖 `SET NX EX 120`（tool.ts） | 120 s | token cache |
- reference range 本身**沒有任何 cache**：同一病人重新整理頁面，300+ 次 RPC 全部重打。

## 5. 風險表與等價驗證
| 風險 | 說明 | 緩解 |
|---|---|---|
| core batch 語意未驗證 | trans 從未在 prod 打過 `…InOutBatch`；不知 core 對缺 item / DB 無資料怎麼回、上限幾筆、單次 300+ items 是否超 message size 或超時 | 先在 staging 用真資料打一次；chunk（如 50/批）；超時 fallback per-item |
| batch 全敗 → 全頁無 range | §2.3 | fallback 到現有 per-item 路徑（保留 `getDetailRangeInfo` 不刪） |
| join 錯位 | 用 `(sample_id,test_id)` string 比對；core 回的型別可能是 number | 統一 `String()` 兩邊 |
| 計算邏輯分叉 | 死碼 batch 版是舊算法 | 把 `getDetailRangeInfo` T:5297-5862 抽成純函式 `computeRangeInfo(All, result)`，單筆與 batch 共用 |
| P1 提前打 HTTPS | 若 `contentList` 為空（D 分支）現況不會打 `full_test_mapping`；提前會多一次呼叫 | 可接受（只是多打一個 cached GET），或在 A 完成後、C 之前 kick |
| `result_value:'0'` 常數 | 若改成傳真值，core 的 `In` 會變但 `All` 不變；為等價**不要改** | |

驗證方式：
1. **Golden-response spec**：照 `trans.service.tnp-retry.lis7790.spec.ts` / `getPatient.service.returnPatient.spec.ts` 的模式，`Object.create(TransService.prototype)` + jest.mock redis/logger/axios/Sentry，stub `referencerangeService.getPatientDetailedReferenceRangeInOut(Batch)` 回 fixture（`All` 含 Range/Value/NO_REFERENCE_RANGE、±999999、空 `All`、缺 item）。對 `getTestReportResultnewrange` 的完整回傳做 `toEqual` 深比對，舊路徑 vs 新路徑同 fixture。fixture 從 staging 真 RPC 錄。
2. **Shadow diff**（照 findPatient PR #769 的做法）：新路徑掛 env flag；flag 開時同時跑舊/新，`JSON.stringify` 深比對、只 log 差異與耗時，回舊結果。跑 1–2 天、比對數千筆後再切。差異排除 `rangeinfo` 順序無關欄位。
3. 觀察 `lis-core-deploymentv7` 的 `GetPatientDetailedReferenceRangeInOut` 呼叫量與 p99 應同步掉。

## 6. 建議 PR 切法與預估
| PR | 內容 | 預估省下（p95 路徑） |
|---|---|---|
| **PR-1**（純 test） | golden spec 覆蓋 `getTestReportResultnewrange` + `getDetailRangeInfo` 現況（含 error 分支） | 0，建 baseline |
| **PR-2** | P1：`getFullTestMapping` 提前與 A 併發；P2：H 三個 HTTP `Promise.all` | 3–4.5 s 的 span 大部分藏到 A+C 後面：**≈ 2.5–4 s**（cache miss 時）；P2 ≈ 0.1 s |
| **PR-3** | 抽 `computeRangeInfo` 純函式（重構，行為不變，spec 綠） | 0 |
| **PR-4** | batch：去重 → 剔除 NutriPro → chunk 送 `GetPatientDetailedReferenceRangeInOutBatch` → 以 key join → `computeRangeInfo`；失敗 fallback per-item；env flag + shadow diff | 300 併發 RPC（1.5 s wall, core 端 0.4–1.5 s/次）→ 幾個 batch 呼叫（估 100–400 ms）：**≈ 1–1.3 s**，並移除 core 的 300× 突發負載 |
| **PR-5**（需 Leo 決定） | P3 issue 併發；`EXPIRE 1` 是否加長；`samples[0]` 只比第一支 accession 的 500 是否要修 | 0.4 s；error rate 可降 |

順序建議 PR-1 → PR-2 → PR-3 → PR-4；PR-2 收益最大且不碰 gRPC 語意，先做。全部完成後 p95 由 6.1 s 估降到 ~1.5–2 s（剩 getPatient/issue/orderV2 的 serial 鏈與 core 本身延遲）。
