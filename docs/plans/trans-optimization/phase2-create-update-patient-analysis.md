# Phase 2 — `POST /utility/createPatient` / `PUT /utility/updatePatient` 呼叫圖與優化計劃

- 日期：2026-09-14
- 分析對象：`LIS-transformer` `origin/main` @ `2716968`（detached worktree `~/src/LIS-transformer-cp`，唯讀）
- 入口：`src/utility/utility.controller.ts:2425-2483`（createPatient）、`:2549-2586`（updatePatient）→ `src/utility/utility.service.ts:11004-11183`（`createPatient`）、`:11185-11290`（`updatePatient`）
- 同一個 service method 也被 API product 的 `POST/PUT /v1/patients` 共用（`src/utility/public-patients.controller.ts:114`、`:178`），修 service 兩邊同時受益
- Datadog 基線（任務給定，7d）：createPatient p95 4.5 s / p50 3.9 s / 2,072 calls；updatePatient p95 4.1 s / p50 1.4 s / 710 calls
- 最高原則同 PLAN.md：**功能零改變**。這兩條是 write path，副作用集合與順序都要能證明相同。

## 0. 先講結論（p50 為什麼高）

| 端點 | 端點 p50 / p95（7d APM，sampled） | 其中 core v1 gRPC | 其中 trans 自己 |
|---|---|---|---|
| `POST /utility/createPatient` | 3.77 s / 4.61 s（n=273） | `CreatePatientV2` 0.82 s / 1.31 s（n=271） | **~2.9 s：14 次串行 Kafka connect→send→disconnect**（PVS 事件 7 欄位 × 2 個 cluster） |
| `PUT /utility/updatePatient` | 1.87 s / 3.55 s（n=50） | `UpdatePatientInformantWithWriteBack` 1.84 s / 3.48 s（n=50） | ~40-80 ms（2 個 Redis 讀 + 1 個 `ListClinicCustomersByClinicID` 68 ms） |

- createPatient 的「每一通都慢」不是尾巴、不是 retry、不是 sleep，是 `utility.service.ts:11071-11162` 那個 for-loop：每個有值的 demographic 欄位各發一則 Kafka 訊息到 on-prem Kafka **和** Azure Event Hub，而 `sendKafkaMessage`（`:4127-4193`）／`sendKafkaMessagev2`（`:4194-4245`）**每次呼叫都 `new producer()` → `connect()` → `send()` → `disconnect()`**。prod trace `6aa887ae000000002ada85eeac0cf48e`（4.55 s）：`CreatePatientV2` 0.91 s（23:47:58），之後 23:47:59 → 23:48:03 全部是 14 個 `kafka.produce`（每個 42-166 ms）+ 14 個 `tcp.connect`（7-44 ms）+ DNS，TLS/SASL 握手與 disconnect 沒有 span，平均一個 cycle ≈ 280 ms。
- updatePatient 慢在 core 端（trans 佔比 < 5%），trans 側能省的只有幾十 ms；真正的 1.8 s 在 `LIS-backend-coreSamples` `patient.service.ts:1108` `updatePatientInformantWithWriteBack` 的**逐欄位** `record_audit_log` gRPC + 本地 Kafka `client.connect()`+send + EventHub send（origin/main `:1318-1450`）。本文件只記錄、不動 core。

## 1. Call graph（執行順序、迴圈、依賴、失敗語意、副作用）

符號：`[A]`=lis-core v7 gRPC（`microserviceOptions`，`trans.grpc.options.ts:6-38`：`CORE_RPC_STAGE`，30 s timeout，**retryPolicy 5 attempts / backoff 1→2→4→8 s on UNAVAILABLE|UNKNOWN，套用到 `lis` package 全部方法含寫入**）、`[V2]`=coresamplev2 gRPC（`CORE_SAMPLE_V2_RPC`，無 retryPolicy）、`[R]`=Azure Redis、`[K]`=Kafka、`[L]`=winston console log（同步，無 I/O）。

### 1.1 createPatient

| # | 位置 | 呼叫 | 迴圈 | 依賴 | 失敗語意 | 副作用 |
|---|---|---|---|---|---|---|
| C0 | controller `:2425` | `CustomJwtAuthGuard`（`auth/custom-jwt-auth.guard.ts:37-67`）：`jwt.verify`，HS256 secret 來自 env（`auth/constants.ts:12-28`），RS256 每次 `fs.readFileSync('rsa-key')` | – | – | 401 | 無 |
| C1 | controller `:2433-2462` | `resolveIdsForHttpOptional`（純函式）；customer_id 取 body 否則 JWT，缺→400 | – | – | 400 | 無 |
| S1 | service `:11017` → `:10970-11002` | `isMandatoryDobSexEnabled` → `[V2] CustomerService.FetchCustomerBetaProgramsForClinic`（**未帶 metadata**：無 authorization、無 x-request-id；p50 73 ms / p95 167 ms） | – | customer_id/clinic_id 皆 0 時跳過 | 任何錯誤→`false`（fail-open：驗證被跳過）+ `[L]` | 無 |
| S1b | `:11018-11021` | `missingDobSexMessage` 純函式；缺 DOB/Sex→`{400}` | – | S1 | 400，**不建病人** | 無 |
| S2 | `:11025-11026` | `settingTool.createMetadataForCoresampleV2` **呼叫兩次**（`metadata`、`oauth2metadata` 內容完全相同，prod 用前者）→ `getOAuthToken`（`setting/tool.ts:105-215`）：in-memory fast path；若在 5 分鐘 buffer 內背景觸發 `[R] SET NX EX 120`（trace 裡兩個 ~1 ms 的 SET 就是它） | – | – | token 失敗→空 Bearer，不擋 | `[R]` 寫 lock key（背景） |
| S3 | `:11033-11068` | `[A] PatientService.CreatePatientV2`（`protos/patient.proto:68`；p50 825 ms / p95 1.31 s） | – | S1b 通過 | gRPC throw→外層 catch→`{500}`；core 回 `internal_call_code>=400`（含 duplicate，`data` 帶既有病人）→controller 原樣回 status | **core 寫入**（core 端 `createPatientWithBullWriteBack`：3-4 個 dup-check query、insert、audit gRPC、Kafka sync、Bull queue） |
| S4 | `:11071-11162` | PVS 事件：`demographicFields` 7 個（first/last/dob/sex/email/phone/address），有值者各發 `sendKafkaMessage(lis-general-events)` 再 `sendKafkaMessagev2(general-sample-events)`，**全部串行 await** | 最多 7 × 2 = 14 次 | `created_patient_id` 且 code<400 | 兩個 helper 內部 try/catch，失敗回 `{500}`；**呼叫端不檢查回傳值**→靜默略過該則、繼續下一則；外層 catch 只吃 throw，寫 `[L]`，**不影響 HTTP 回應** | `[K]` 每則：新 producer、connect、send、disconnect；partition key = patient_id |
| S5 | `:11165-11169` | 回 `{internal_call_code, message, data}` | – | – | – | – |

順序約束：S1 → S1b → S3 是硬順序（驗證必須擋在寫入前）；S3 → S4 硬順序（需要 patient_id）；S4 內 14 則彼此獨立，只要求同 topic 內 7 則先後順序（同 partition key，PVS 消費端可能依序 overwrite）；local 與 Azure 兩條完全獨立。

kafkajs client 設定（影響尾巴）：on-prem `utility.kafka.ts:11-20`（connectionTimeout 2 s，retry 8 次 maxRetryTime 60 s，`allowAutoTopicCreation: true`）；Azure `utility.kafka.azure-gen.ts:11-32`（ssl + SASL PLAIN，**connectionTimeout 60 s**，retry 5 次）。Event Hub 不通時單一則訊息就能卡到分鐘級，且會重複 7 次。

### 1.2 updatePatient

| # | 位置 | 呼叫 | 迴圈 | 依賴 | 失敗語意 | 副作用 |
|---|---|---|---|---|---|---|
| C0/C1 | controller `:2549-2566` | 同上；`clinic_id` 必填（缺→resolve 失敗） | – | – | 400/401 | 無 |
| U1 | `:11194-11200` → `trans.service.ts:18876-18917` | `trans.checkPatientCustomer`（ownership gate）| – | – | 回 falsy→`{403}` | 見 U1a/U1b |
| U1a | `trans.service.ts:13005-13050` | `getPatient`：`[R] GET lis_frontend_service_patientv2_{id}`（TTL 120 s，`src/redis.ts` ioredis 直連）miss→`createMetadataForCoresampleV2` + `[A] PatientService.GetPatient`（p50 43 ms / p95 444 ms）→`[R] SET EX 120` | – | – | 任何錯誤吞掉、回 `undefined`→上層 `pati.patient_customer_ids` TypeError→被 U1 catch→回 `undefined`→**403** | `[R]` 寫 cache |
| U1b | `trans.service.ts:13121-13180` | `listClinicCustomersByClinicID`：`[R] LRANGE lis_frontend_service_listClinicCustomersByClinicID_{clinic}`（nestjs-redis client，**TTL 5 s**）miss→metadata + `[A] ClinicService.ListClinicCustomersByClinicID`（p50 68 ms / p95 142 ms）→`RPUSH` + `EXPIRE 5` | – | **與 U1a 串行但互不依賴** | 錯誤→`[]`→不擁有→403 | `[R]` 寫 cache |
| U2 | `:11207-11210` | `createMetadataForCoresampleV2` ×1 | – | – | 同 S2 | 同 S2 |
| U3 | `:11213-11258` | 組 `rpcRequest`：只轉送有提供的欄位；`patient_apt_po` 允許空字串（清除）；`address_line_2` alias | – | – | – | 無 |
| U4 | `:11260-11265` | `[A] PatientService.UpdatePatientInformantWithWriteBack`（`protos/patient.proto:71`；p50 1.84 s / p95 3.48 s） | – | U1 通過 | throw→`{500}`；core code 原樣回 | **core 寫入**：patient 166 + 153 write-back、address/contact upsert、Bull queue、逐欄位 audit gRPC + 2 個 Kafka |
| U5 | `:11267-11270` | 回 `{internal_call_code, message}` | – | – | – | **不失效 trans 自己的 `lis_frontend_service_patientv2_{id}`（120 s）** |

prod trace `6aa8844c00000000360a5119e28b8838`（2.16 s）：Redis GET/LRANGE/SET/RPUSH/EXPIRE 各 ~1 ms、`ListClinicCustomersByClinicID` 54 ms、`UpdatePatientInformantWithWriteBack` 2.10 s。trans 側總開銷約 60 ms。

## 2. 哪些等待是那 3-4 秒

1. **createPatient S4（主犯，每通都有）**：14 × (DNS + TCP + TLS/SASL 握手 + metadata + produce + disconnect) ≈ 2.9 s p50。純 produce 本身 p50 只有 75-80 ms（7d：`kafka.produce` general-sample-events 75 ms、lis-general-events 79 ms；`tcp.connect` 18-24 ms），其餘都是連線建立/拆除。
2. **createPatient S3（次要）**：core 端 0.8 s，含 dup-check 與 audit/Kafka；trans 無法改。
3. **updatePatient U4（全部）**：core 端逐欄位 audit + Kafka，欄位越多越慢（p95 3.5 s）；trans 無法改。
4. **尾巴候選（非 p50）**：`[A]` retryPolicy 最多 1+2+4+8 = 15 s backoff + 30 s timeout；Azure Kafka connectionTimeout 60 s × 重試；on-prem Kafka retry 最長 60 s。這些是 p99 而非 p95 的來源。
5. 沒有 fixed sleep、沒有 email、沒有 HTTP 到其他服務、沒有 core v1 HTTP（見 §4）。

## 3. 可平行 vs 必須保序

| 項目 | 判定 | 理由 |
|---|---|---|
| S1 ∥ S2 | 可以但無意義 | S2 是 in-memory（~0 ms） |
| S1b 必須在 S3 前 | **保序** | 驗證失敗不得寫入 |
| S3 必須在 S4 前 | **保序** | 需要 `patient_id` |
| S4 local topic ∥ Azure topic | **可平行** | 不同 cluster、不同 consumer |
| S4 同 topic 7 則 | 可合併為**一次 `send({messages:[7]})`** | 同 partition key，單一 batch 內順序即陣列順序，PVS 看到的先後與現在相同；不建議 7 個獨立 `send` 用 `Promise.all`（kafkajs 不保證跨 send 的送達順序） |
| U1a ∥ U1b | **可平行** | 互不依賴；兩者錯誤語意都是「吞掉→403」，`Promise.all` 後結果相同 |
| U1 必須在 U4 前 | **保序** | ownership gate |
| S4 移出 request path（回應後再發） | 可行但**不是零改變** | HTTP 回應內容不變（S4 的錯誤本來就不影響回應），但 pod 在回應後被殺會丟事件；需產品同意 |

## 4. Core v1 HTTP（VP-18156）

- 這兩條路徑**都不走** `process.env.create_patient` / `create_patientv2`。那兩個 env 只在 `createPatientBatch`（`utility.service.ts:8134`，`axios.post` 帶呼叫者 Bearer）與 `createPatientBatchv2`（`:8342`，帶固定 `create_patientv2_token`）→ `POST /utility/createPatientBatch`、`/createPatientBatchv2`（controller `:1510`、`:1537`）。Phase 3.1 量到 27.9 h 內流量 0。
- gRPC 替代品就是 createPatient 已在用的 `[A] PatientService.CreatePatientV2`（`protos/patient.proto:68`；request `:91-131` 含 batch v1 payload 用到的 `uploaded_status`/`uploaded_vg_status`/`patient_country_id`/`clinic_id`）。coresamplev2 也有同名 RPC（`protos/coresamplev2/patient_service.proto:86`），但 `utility.service.ts:242-252` 的產品決定把病人 RPC 釘在 core v1。
- 順帶：`:242-252` 註解說「`ListPatientRecords` 不存在於 v2 proto」，但 `protos/coresamplev2/patient_service.proto:123` 已有；註解過時，行為不受影響。

## 5. Redis

| 路徑 | key | client | TTL | 備註 |
|---|---|---|---|---|
| S2/U2 背景 | `lis_frontend_service_oauth_fetch_lock` | `src/redis.ts` ioredis | 120 s | SET NX，每次 `getOAuthToken` 在 buffer 內都會打一次（trace 每通 2 次，各 ~1 ms） |
| U1a | `lis_frontend_service_patientv2_{patient_id}` | `src/redis.ts` ioredis | 120 s | **updatePatient 成功後不失效**；`listPatientsBatch`（`trans.service.ts:13101`）同 key 但 TTL 20 s |
| U1b | `lis_frontend_service_listClinicCustomersByClinicID_{clinic_id}` | `@liaoliaots/nestjs-redis` `RedisService` | 5 s | TTL 太短，幾乎每通 miss；同一 process 兩套 Redis client 連同一台 Azure Redis |

createPatient 路徑本身沒有任何業務 Redis 讀寫。

## 6. Risk table

| 變更 | 風險 | 緩解 |
|---|---|---|
| 長連線 producer（module-level singleton） | Event Hub / on-prem broker 閒置斷線後第一次 send 要重連（kafkajs 自動重連，但會多一次連線延遲）；pod 生命週期內連線洩漏 | `onModuleDestroy` disconnect；send 失敗時 reconnect 一次再重試；先只換 `sendKafkaMessage`/`v2` 兩個 helper 的內部，外部簽名與 testaks 改道（`:4134-4149`、`:4201-4208`）不動；repo 有既成模式 `calendar/kafka/kafka.service.ts:44-49` |
| 7 則合併成一次 send | 單 batch 變大（7 × ~600 B，可忽略）；若 PVS 消費端假設「一則一 connect」— 不會，Kafka 端看不出差別 | 保持陣列順序 = 現在的 for 順序 |
| local ∥ Azure | 一邊失敗另一邊照發 — **現況就是這樣**（各自 try/catch） | 無新增風險 |
| U1a ∥ U1b | 無語意差異 | – |
| 刪掉重複的 `createMetadataForCoresampleV2` | 無 | 兩個變數內容相同，prod/非 prod 都只用一份 |
| S4 移出 request path | 事件丟失面變大；違反零改變（timing） | 列為 PR5，需 Leo/產品拍板 |

## 7. 建議的 PR 順序（每個都可獨立上）

| PR | 內容 | 預估 createPatient p50 | 預估 updatePatient p50 |
|---|---|---|---|
| 現況 | – | 3.8 s | 1.9 s |
| PR1 | `sendKafkaMessage`/`sendKafkaMessagev2` 改用兩個長連線 producer（lazy connect、失敗 reconnect 一次）。**注意 blast radius**：repo 內 64 個 `.producer(` 呼叫點中所有走這兩個 helper 的路徑都會受益，也都會受影響 | 每 cycle 280 → ~80 ms：≈ 2.0 s | 不變 |
| PR2 | S4 改成「每 topic 一次 `send` 帶 7 則」+ local ∥ Azure `Promise.all` | ≈ 1.0 s（0.07 + 0.82 + ~0.15） | 不變 |
| PR3 | 刪重複 metadata（S2）；U1a ∥ U1b；順手把 `isMandatoryDobSexEnabled` 補上 metadata（見 §8-6，這條是行為修正要單獨審） | −0 | −50 ms |
| PR4 | core 端（另開 ticket，非 trans）：`updatePatientInformantWithWriteBack` 逐欄位 audit+Kafka 也是每欄位 `client.connect()`，同樣手法可省 1 s 以上 | – | ≈ 0.6-0.9 s |
| PR5（需拍板） | S4 改為回應後發送（`setImmediate`），或改為單一事件由 PVS 端展開 | ≈ 0.9 s | – |

PR1+PR2 之後 createPatient 端點 p50 ≈ core `CreatePatientV2` 本身 + ~0.2 s，再往下只能動 core。

## 8. 看起來像 bug 的地方（只記錄，不修）

1. **producer 洩漏**（`:4158-4170`、`:4211-4223`）：`disconnect()` 不在 `finally`，`send()` throw 時 producer 不會 disconnect，socket 留到 broker 端 idle 踢掉。每失敗一則就多一條懸空連線。
2. **PVS 事件失敗不可見**（`:11127-11139`）：helper 回 `{internal_call_code:500}` 但呼叫端不看回傳值，失敗只留 warn log；客戶端拿到 201，PVS 卻少欄位。是否可接受要由產品定，但至少應該 metric 化。
3. **寫入 RPC 有 client-side retry**（`trans.grpc.options.ts:20-33`）：`CreatePatientV2`/`UpdatePatientInformantWithWriteBack` 在 UNKNOWN（core 端 throw 就會是 UNKNOWN）時最多重送 5 次。create 若在 core insert 之後才失敗，重送會被 dup-check 擋成 4xx「已存在」——病人其實建好了但客戶端看到錯誤；update 重送會產生重複的 audit log 與 PVS 事件。建議對 PatientService 寫入方法設 `retryableStatusCodes: ['UNAVAILABLE']` 或 maxAttempts 1（要單獨評估）。
4. **ownership gate 的錯誤被翻成 403**（`trans.service.ts:13005-13050` → `:18876-18917`）：`getPatient` 任何錯誤（Redis、gRPC）回 `undefined`，上層對 `undefined.patient_customer_ids` 取值 TypeError，被 catch 後回 `undefined`→controller 回 403「Patient does not belong to this clinic」。fail-closed 是對的，但狀態碼誤導，且 `listClinicCustomersByClinicID` 空陣列（clinic 沒有 customer 或 gRPC 錯）也會是 403。
5. **updatePatient 後 trans cache 不失效**（`utility.service.ts:11183` 註解說 core 會做 Redis invalidation，但 core 的 key 是 `lis::core_service::grpc_lock::getpatient::...`，不是 trans 的 `lis_frontend_service_patientv2_{id}`）：更新後 120 s 內，經 trans `getPatient` 讀到的仍是舊資料。
6. **`isMandatoryDobSexEnabled` 對 coresamplev2 呼叫不帶 metadata**（`:10981-10987`）：其他所有 v2 呼叫都帶 OAuth Bearer + x-request-id。今天 v2 沒擋所以 200；一旦 v2 開始驗 token，這個 gate 會因為錯誤而 fail-open→強制 DOB/Sex 驗證靜默失效，且 core 端 log 沒有 request id 可追。
7. `createPatient` 兩次 `createMetadataForCoresampleV2`（`:11025-11026`）與 `inviteCustomerToClinic`（`:11300-11301`）同樣寫法：無害但浪費，且每次都可能觸發背景 Redis SET。
8. `protos` 註解過時：`utility.service.ts:249-251` vs `protos/coresamplev2/patient_service.proto:123`（見 §4）。

## 附：查證方法備忘

- Worktree：`git worktree add --detach ~/src/LIS-transformer-cp origin/main`（@ `2716968`）。core 端只用 `git show origin/main:src/patient/patient.service.ts` 讀，未建 worktree。
- Datadog（us3，`service:lis-trans-deployment env:prod`，7d）：`aggregate_spans` by `resource_name` 取端點與下游 gRPC 的 p50/p95；`kafka.produce`/`tcp.connect` by destination 取每則成本；trace `6aa887ae000000002ada85eeac0cf48e`（create 4.55 s）、`6aa8844c00000000360a5119e28b8838`（update 2.16 s）逐 span 對照。APM span 計數是 retained sample（diversity sampling），與任務給的 2,072 / 710 calls 不同量綱。
- 兩個 trace 都有 `dns.resolve TXT ... ENODATA` 的 handled error（grpc-js 查 service config），13 ms、無害，可忽略。
