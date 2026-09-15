# Trans v1 / v2 優化計劃（草案 v0.3）

- 日期：2026-09-11（v0.2 追加 cloud-local-proxy / web-homepage-api；v0.3 依 Jira 實讀改寫 Phase 3；2026-09-14 Phase 1.1 S1 **已執行**（st + prod），見 §8 runbook）
- 狀態：**draft**。code 側只加了 `TRANS-OPT` 註解（四個 repo 的 `feature/leo/TRANS-OPT` branch，零行為變更，見 §9）；未開 PR、未留 Jira comment。等 Leo review。
- 範圍：`LIS-transformer`（trans v1，REST + gRPC）與 `LIS-transformer-v2`（trans v2，GraphQL + REST）；v0.2 起追加 `cloud-local-proxy`（退役對象）與 `web-homepage-api`（去向待決，見 §2.9 / Phase 5 Track W）
- 最高原則：**功能零改變**。所有變更都必須能證明「對外回應相同、副作用相同」，否則不做。

## 0. 資料來源與可信度

| 來源 | 狀態 | 備註 |
|---|---|---|
| 錄音 `Trans p1.m4a`（25 min）、`Trans p2.m4a`（7.5 min） | 已轉錄（mlx-whisper large-v3-turbo，5 分鐘分段） | 會議為中文口語、多人、音質一般；重點摘要見 Appendix A，原始轉錄在 `raw-transcript/`。人名以會議中稱呼記錄，可能有誤。 |
| VP-17348 Core Service V1 → V2 Migration（Epic） | **已讀**（2026-09-11 經 Jira REST，Atlassian MCP 對本 session 仍不可用；完整 dump 見 Appendix C） | Epic 有 6 個 phase；與 trans 相關的是 Phase 4 read cutover（V1 gRPC reverse-proxy 到 V2，caller 不改）與 Phase 4b Core v1 REST Retirement（VP-18140 ~ 18157）。**VP-18152 的 scope 只有「trans 不再用 core v1 HTTP」**，對應本文 §2.3 的 4 個殘留呼叫；target 09-30，P4 刪 HTTP 10-31。詳 Phase 3。 |
| 兩個 repo | 已 `git pull --ff-only` 到 `origin/main`（v1 `f039348`、v2 `a8243de`） | v1 local 原本落後 18 commits；v2 原停在 feature branch，已切回 main。 |
| AKS `lisportalprod` | **唯讀**盤點（`kubectl get` deploy / svc / cm） | 只取 host，未輸出 secret。完整結果見 Appendix B。 |
| 本地測試 baseline | 兩個 repo 各跑一次 `jest --ci` 與 `tsc --noEmit` | 結果見 §2.7。 |
| Slack「Trans TransV2 speed refactoring & code rewiring」（Ray，2026-09-11 11:19-11:28） | 已納入 | 範圍追加兩個 repo：`Vibrant-America/cloud-local-proxy`（TypeScript，已 unarchive、全員可寫）與 `Vibrant-America/web-homepage-api`（Python，只部署在地上 `60.6` ns `lis`，與 cloud-local-proxy 同 namespace，pod 名 `vw-page-deployment`）。昊哥先前打算把兩者都下掉併進 trans；兩者都是 yuxuan 手動推、沒有更新過 CI/CD。地上 ns `lis` 現況：cloud-local-proxy 3 pods + st 1 pod、vw-page 3 pods（Ray 貼的 `kubectl get pods -n lis`）。兩 repo 已 clone 到 `~/src`，盤點見 §2.9。 |

**Leo 已拍板（2026-09-11）**：Phase 4 的 v1 `LoggingInterceptor` 不再序列化整包 request / response，**不算功能變更**。dream pipeline 已完成一輪，前一版提到的停擺疑慮解除。

## 1. 會議結論（Trans 的定位、問題、期望）

**Trans 為什麼存在（兩個理由，都不能被優化掉）**
1. Core 出於 PHI 安全考量正在變成純 gRPC、不對外開 HTTP；前端要拿 PHI 只能經過 Trans。Trans 是 PHI 的唯一 HTTP 出口。
2. Trans 為前端做聚合：前端一次打 Trans，Trans 下游收集多個服務再回。

**問題（會議陳述 + 本次盤點證實）**
- P95 特別高，尤其高峰期；以 2 秒為門檻，約有 10 ~ 20 支 API 超標（Datadog）。沒人有時間查原因。
- 「套娃」：2023 年 Azure 與 on-prem 網路未打通時，雨萱（音）建了 `cloud-local-proxy`（雲上、地上各一套）讓 HTTP 繞過網路隔離；網路早已打通（浩哥/Hawk），但 proxy 仍有流量。範例：某前端 → cloud-local-proxy HTTP → Trans HTTP → order/shipping HTTP 拿 PDF；transv2 的 `checkIfPersonalizedReportCanBeCreated` 仍打 cloud-local-proxy。
- Trans 內有「從頭到尾只包 HTTP、沒有任何 RPC」的端點，這種端點沒有存在必要（前端可直接打目標服務）。
- Trans 有 100+ 環境變數，多數是服務位址；多人用 `kubectl apply -f` 帶舊檔覆蓋，已多次把「已遷到雲上的 URL」打回地上。
- Core 團隊（志斌/周凡）只優化「跟 Core 相關」的 Trans 路徑，其餘要由 Trans 側自己發現、自己解。

**期望的做法**
- 不是修 bug，是「看 P95、找問題、修掉」。
- 仿 Core Migration epic 的模式：先定大方向 phase → 每個 phase 出一份詳細設計 doc → Rui review → 開票 → 動工。
- 若 Trans 裡包 report 的端點沒必要，可以從 Trans 拿掉，讓前端直打 report 服務。

## 2. 現況盤點（事實，附證據位置）

### 2.1 對外表面（= 必須保持不變的契約）

| 服務 | 表面 | 數量 | 契約快照來源 |
|---|---|---|---|
| trans v1 | REST（29 controllers） | 318 routes（150 GET / 129 POST / 22 PUT / 4 PATCH / 13 DELETE） | Swagger `/api`（`src/main.ts:51-57`） |
| trans v1 | gRPC `listrans.TransService` | 5 methods：GetSampleInfo、GetSampleInfoV2、GetPatientPageStatus、GetKitStatus、GetReporteStatus（`src/utility/utility.controller.ts`） | `protos/trans-service-protos/trans_service.proto`；**消費者：LIS-Shipping、LIS-Sample、LIS-backend-results-grpc**（三個 repo 都 vendor 了此 proto）→ 不可移除 |
| trans v2 | GraphQL | 123 Query / 66 Mutation / 39 ResolveField / 4 Subscription | `schema.gql`（3,423 行，repo 已 track，但 `autoSchemaFile: true` 不會自動更新，需人工 regenerate） |
| trans v2 | REST | 192 routes（89 GET / 77 POST / 13 PUT / 3 PATCH / 10 DELETE） | Swagger |

前端呼叫路徑（va-portal / vibrant-wellness-portal / pns-portal）：`/v1/portal/trans-service` → v1；`/v2/portal/trans-service` → v2。三個前端 repo 內**沒有**直接引用 cloud-local-proxy；錄音提到的「前端 → cloud-local-proxy」屬其他前端（未在本機，見 §7）。

### 2.2 部署與交付管線

| 項目 | trans v1 (`default/lis-trans-deployment`) | trans v2 (`transv2/lis-transv2-deployment`) | cloud-local-proxy (`cloud-local/`) |
|---|---|---|---|
| replicas | 3（repo yaml 寫 2） | 3 | 3（+ st 1） |
| resources | requests.memory 2Gi，無 limits、無 CPU request | requests.memory 1536Mi，其餘無 | 無 |
| probes | liveness + readiness | liveness + readiness | **無** |
| image | SHA-pinned | SHA-pinned | **`:latest`** |
| HPA | 無 | 無 | 無 |
| ConfigMap keys | 154（96 個是 URL/位址） | 152（89 個 URL/位址） | 57 explicit env |
| CI/CD | GitHub Actions push `main` → `az acr build` → `kubectl set image`；**無 test / lint / typecheck step** | 同（`Azure/k8s-deploy`）；**無 test step** | 不明（repo 不在本機） |
| Node | 22（Dockerfile.prod） | 20 | — |

repo 內的 `lis-trans-k8env.yml` 只有 5 個 key，cluster 上 154 個 → ConfigMap 的唯一真相在 cluster，repo 檔案不可拿來 apply（錄音提到的回滾事故就是這個）。

### 2.3 Core 呼叫路徑（與 VP-17348 / VP-18152 的交集）

- **trans v2**：20 處 `process.env.SERVER_ENVIRONMENT === 'prod' || process.env.FORCE_CORE_V1_STAGING === 'true'` 散在 12 個檔案（`calendar.service.ts:83`、`customer.service.ts:51`、`dashboard.service.ts:91`、`trans/setting.service.ts:125,4077`、`patientProfile.service.ts:206`、`utility.api.service.ts:197,365`、`service.ts:209`、`PNS.service.ts:208`、`payout-setting.service.ts:66`、`api-credential.service.ts:68`、`setting/setting.service.ts:204`、`utility/utility.service.ts:237,2958,3168`）。語意：**prod 走 core v1 gRPC（package `lis`），staging 走 core v2 gRPC（`coresamples_service`）**。另有 `*_RPC_CLOUD` 雙 client + `withCloudFallback`（`calendar/shared/with-cloud-fallback.util.ts`，kill switch `GRPC_CLOUD_FALLBACK_ENABLED=false`）。
- **trans v1**：主要用 core v1 gRPC `lis`（`src/trans/trans.grpc.options.ts:6-38`，含 30s timeout + 5 次 retry），`coresamplev2` client 已存在並在 14 個檔案使用；`trans.grpc.options.ts:142-147` 算出的 `coreSampleV2Url` **沒有被用到**（第 152 行仍直接讀 `CORE_SAMPLE_V2_RPC`，dead code）。
- **殘留的 core v1 HTTP**（VP-18156 要刪的表面）：v1 讀 `create_patient`、`create_patientv2`、`list_customer_by_id_carlos` 各 1 處，**另有 `LOG_IN_VIA_SESSION`（`utility.service.ts:254` `login()`，由 `GET /utility/login` 曝露；v0.1 誤判為無人讀，subagent 3.1 更正，流量為零）**；v2 讀 `list_customer_by_id_carlos` 1 處。目標 `lis-core-http-service.default.svc.cluster.local:30112`。實測流量見 Phase 3.1。
- **lis-order HTTP**（`lis-order.default.svc.cluster.local:4242`）：v1 讀 `GET_ORDER_CARLOS` 14 處、`getProviderAndClinicName` 5、`getQuestionnaireRequiredMap` 5 等；v2 `GET_ORDER_CARLOS` 6、`get_pns_info` 6。這是 Order Service Rewrite（VP-15855）的範圍，本計劃不動，但要列進相依。

### 2.4 套娃盤點（prod ConfigMap 值 × code 是否仍讀取）

| # | 服務 | env key | prod 值指向 | code 讀取 | 判定 |
|---|---|---|---|---|---|
| S1 | v2 | `checkIfPersonalizedReportCanBeCreated` | ~~`cloud-local-proxy-service.cloud-local:3047/old-report/...` → proxy 再打 `192.168.60.77:8081`~~ → **2026-09-14 已改直指 `192.168.60.77:8081/.../CheckIfPersonalizedReportCanBeCreated?sampleId=`（st + prod）** | `patientProfile.resolver.ts:339` | **已去套娃**（Phase 1.1 完成；雲上 cloud-local-proxy 已知 caller 歸零，1.6(d) 的 30 天計時從 09-14 起算） |
| S2 | v2 | `proxy_getkit` ×4、`proxy_getteststatus`、`proxy_getQuestionaire` | `lis-trans-service.default:3146/proxy/grpc/*` → v1 再打 gRPC | `patientProfile.service.ts:725,976,1553,1568,1613`、`utility.service.ts:2577` | **活的套娃**（v2 → v1 HTTP → gRPC；v2 自己就有同一組 gRPC client） |
| S3 | v2 | `getSetting`、`get_setting`、`get_setting_tokne` | `lis-trans-service:3146/utility/getSetting*` | `PNS.service.ts:405`、`PNSResolver.resolver.ts:316,320` | v2 → v1 HTTP。是否為套娃要看 v1 getSetting 的聚合邏輯能否在 v2 等價重現（v1 `getSetting` 是 73 個 utility route 中最重的一支） |
| S4 | v2 | `va_events` | `lis-trans-service:3146/events/samples/get-events` | `utility.api.service.ts:2340` | v2 → v1 calendar module HTTP |
| S5 | v2 | `skin_placepatientorders` | `lis-trans-service:3146/proxy/grpc/sendSkinPlacePatientOrders` → v1 → `www.vibrant-america.com/crmapi` | `utility.service.ts:3277,3330` | v2 → v1 → 公網 HTTP，兩層 |
| S6 | v1 | 14 個 key（`proxy_getkit/getresult/getteststatus/getQuestionaire/getTnpCode`、`Get_Requisitionv2`、`url_*_new`、`url_*v2`、`url_generateOnlineZipNoJWT`、`url_GenerateProducctSummaryReport`） | `api.vibrant-america.com/v1/lis/cloud-proxy` | **0 處** | 殘留設定（`docs/proxy-migration-configmap.md` 已說明），可清 |
| S7 | v2 | `Get_Requisition`、`url_GenerateBatchReqOrReportV2` 等 8 個 | `192.168.10.153:8081`（AKS 不可達的 on-prem IP） | 0 處 | 殘留設定，可清 |
| S8 | v1 | 55 個 key | `api.vibrant-wellness.com/...` 公網 ingress，目標其實是同 cluster 服務（base-report、shipping、accounting、samples、interactive-report、charging…） | 多數有讀（如 `shippin_address` 6、`getinvoice` 4、`inventory_url` 4、`sample_url` 3） | **公網回繞**：v2 對同一批服務已改用 `*.svc.cluster.local`。每次呼叫多走一趟 TLS + WAF + ingress |

cloud-local-proxy 本身（`cloud-local-proxy-config` 55 keys）前面擋的是：on-prem report server `192.168.60.77:8081`、`lis-core-http`、`lis-order`、base-report、statement、oauth、`portal/order`、`crmapi`、`patient-portal-backend`，以及 core/audit/dashboard/issue/shipping/test-connect 的 gRPC。

本機可見的 cloud-local-proxy caller（grep 全部 `~/src` repo）：
- transv2 prod ConfigMap（S1）。
- **`LIS-backend-billing`（Java）** `ProZOrderServiceImpl.java:115` 寫死 `https://www.vibrant-america.com/lisapi/v1/lis/cloud-proxy/grpc/sendSkinPlacePatientOrders`（走 on-prem 公網 ingress 進地上那套 proxy）。這是之前沒人知道的 caller。
- 錄音提到的 legacy report 呼叫者與「某前端」不在本機 repo 內，需 ingress log（見 Phase 1.6）。

### 2.5 已知熱點（有證據的）

| 端點 | 證據 | 現況 |
|---|---|---|
| v1 `POST /trans/findPatient` → `getPatient.service.ts returnPatient`（L369-1166，797 行） | VP-18197 commit `a705662`：VP-17796 在每次 findPatient 末尾 await accounting `/charge/balance`（整頁 200+ sample_ids），p95 從 ~2.5s 惡化到 7-13s（Datadog，2026-08-26 起）；09-10 已拆掉、欄位留 null | 仍有 3 個 for-loop、`listCustomerPatients` + `listCustomerPatientsCount` 兩次 gRPC、`getIssue`/`getPatientIssue`/`getWarning`/`getFedExTrackingNumbers` 各自 await；只有 2 個 `Promise.all` |
| v1 `getTimeLine`（`trans.service.ts:23630-24230`，600 行） | LTM 記錄為常見慢點；有專門分析 doc `docs/getTimeLine-shipping-status-analysis-zh.md` | 2 次 `serviceToken` + 2 次 `getRequest` HTTP；1 個 `Promise.all` |
| v2 `patientProfile` resolved fields | S2：對同一 sample 打 `proxy_getkit` 最多 4 次（經 v1） | `patientProfile.service.ts` 內已有 9 組 redis get/set 與 6 個 `Promise.all`，但仍有 3 處 `getSamplesByAccessionId` 重複 |
| v2 `PNS` resolver | 19 個 `@ResolveField`，每個 field 各自打下游 HTTP（`get_pns_info` 6 處）；`PNS.service.ts` 只有 1 處 redis | 沒有 DataLoader / request-scoped memo（全 repo 0 處 `dataloader`） |
| 會議提到的 Core Info V2 | patient / customer 判斷後串行拿 name、calendar；周凡已改 `Promise.all` | 已修的模式，可複製 |
| v1 `trans.service.ts` 25,665 行 | 12 個 method 超過 500 行（`sharePaymentCompleted` 1000、`shareShippingEmailPNS` 959、`getTestReportResultnewrange` 884、`getTubeInfo` 848…） | 可讀性與測試性是效能工作的前置成本 |

啟發式掃描「for-loop 內直接 await」（N+1 候選）：v1 `old-report.service.ts` 4、`trans.service.ts` 3、`getPatient.service.ts` 2；v2 `event.service.ts` 3、`google-inbound-sync` 3、`utility.service.ts` 2、`utility.api.service.ts` 2、`patientProfile.service.ts` 2。要逐一人工確認。

### 2.6 觀測性現況

- Datadog APM 已在用（VP-18197 用 Datadog 量 p95；pod 由 admission 注入 `DD_*`），兩 repo 的 `package.json` 都沒有 `dd-trace`（自動注入）。
- v1 `LoggingInterceptor`（`src/logging.interceptor.ts`）**對每個 HTTP 請求 `JSON.stringify` 整個 request body 與 response body** 寫 log（只排除 `getSetting` 的 response）。這是 CPU 成本，也是 PHI 進 log 的路徑。v2 的 interceptor 只記 method/url/status/duration，並對 >1s 的請求記 slow metric。
- VP-18140（P0，Global HTTP interceptor structured request logging）與 VP-18141（P0，Dashboard v1 HTTP vs v2 rpc dual curve）是 core 側同主題的票，量測層應對齊而不是各做一套。

### 2.7 測試與建置 baseline（2026-09-11 本機，`npx jest --ci`、`npx tsc --noEmit -p tsconfig.build.json`）

| repo | suites | tests | tsc | 紅燈成因 |
|---|---|---|---|---|
| v1 | 46（**17 fail** / 29 pass） | 581（15 fail） | 1 error | (a) 環境：Redis `192.168.62.79:4647` ECONNREFUSED（58 次）；(b) 本機 `node_modules` 過舊，缺 `@google-cloud/bigquery`（PH-905 新增依賴）→ 10 個 suite 無法載入、tsc 也因此 1 error；(c) stale mock：`settingsTool.createMetadataForCoresampleV2 is not a function`、`this.patientInfo is not a function` |
| v2 | 52（**7 fail** / 45 pass） | 723（16 fail、4 skip） | clean | (a) stale mock：`setting.createOAuth2Metadata is not a function`；(b) `prisma.service.spec.ts` 是需要真 DB 的 integration test 卻沒被 ignore；(c) `practice_event_type` 兩個 GraphQL spec、`daily-report`、`clinic-charting` |

> 結論：**目前沒有一條可信的自動化防線**——CI 不跑測試，本機測試又有紅燈。任何「不影響功能」的宣稱在 Phase 0 前都只能靠人工比對。

### 2.9 追加範圍：cloud-local-proxy 與 web-homepage-api（2026-09-11 Ray 於 Slack 指定）

| 項目 | `cloud-local-proxy` | `web-homepage-api`（pod `vw-page`） |
|---|---|---|
| 技術 | NestJS，Node 16，約 3,500 行 | Python 3.10 FastAPI + MongoDB（odmantic/motor）+ MySQL（`lis_re.order_table`）+ auditlog gRPC，約 5,300 行 |
| 最後 commit | 2026-08-05 Ray（PR #19 移除死路由 `getSampleInfoData`） | 2025-10-23 fionliang（CORS fix） |
| 路由 | 18 條，兩個 controller：`/grpc/*` 6 條（getKitStatus、getPatientTestsResult、getTestStatus、getQuestionaireBySampleId、listTnpCode、sendSkinPlacePatientOrders）；`/old-report/*` 12 條（GenerateBatchReqOrReportV2、GenerateOnlineZipDownloadV2、downloadTestOrderPDF、GetSpecificReports、GenerateOnlineSummaryReport、GenerateProducctReport / SummaryReport、getRequisitionForm、getOrderSummaryReportZip、oneClickPersonalizedReport、checkIfPersonalizedReportCanBeCreated…） | 72 條（prefix `/v1/webpage`），絕大多數是**行銷官網 CMS**：subscribe / patientsignup / contactus / applyjob（Postmark、HubSpot）、science research、team、webinar、testing list、announcement、test info、shortURL（short.io）、education center（HubSpot HubDB 多語系）。**與 LIS 相關的只有 report action 三條**：`getAllReportActions`、`getIndividualReportCount`、`createReportActions`（Mongo 存 view / download / share 計數，HMAC 驗證） |
| 與 trans 的重疊 | **全部 18 條在 trans v1 都已有同名實作**：`src/proxy/proxy.controller.ts`（`/proxy/grpc/*`）與 `src/proxy/old-report.controller.ts`（`/proxy/old-report/*`，VP-17284 時 inline 並加了 PHI ownership gate）。proxy 端的 `/old-report/*` 有 `UnifiedAuthGuard` 但**沒有** trans 那層 ownership gate | 無重疊。trans 沒有 Mongo、沒有 HubSpot / Postmark 行銷流程 |
| 已知 caller | transv2 prod（S1）；`LIS-backend-billing` Java（sendSkinPlacePatientOrders，走地上 ingress）；其他未知 | `va-portal` PatientProfilePage `UserActionService.js`（`www.vibrant-wellness.com/v1/lis/vw-page/v1/webpage/`）、`report-pdf` `UserActionService.js`（`api.vibrant-wellness.com/v1/lis/vw-page/...`）、`ehr-frontend` `report-service.js`（`www.vibrant-america.com/lisapi/v1/lis/vw-page/...`）——三個前端都只用 report action；官網（vibrant-wellness.com 本體）的 caller 不在本機 |
| 部署 | Jenkins：build → 推 on-prem registry `192.168.60.9:6004` → `ssh yuxuan@192.168.60.6 kubectl rollout restart -n lis`。**雲上 `cloud-local` ns 那套（3 replicas，`:latest`）不在 Jenkinsfile 內，是手動推的**。Jenkinsfile 內含寫死的 registry 帳密 | Jenkins：推 `192.168.60.10:6004/vibrant/webpage-api:latest` → 同樣 `ssh yuxuan@192.168.60.6 kubectl rollout restart deployment/vw-page-deployment -n lis`；staging stage 被註解掉；test stage 被註解掉；Jenkinsfile 同樣含寫死帳密 |
| 測試 | 10 個 spec 檔（未跑） | `tests/` 0 個檔案 |
| 判定 | **可退役**：路由已被 trans v1 完整承接，工作只剩「把 caller 改指向」與「雙集群 scale-to-0」 | **不建議整包併進 trans**：它是官網後端，資料在 Mongo，與 PHI/trans 定位無關。只有 report action 三條值得討論搬家（見 Phase 5 Track W） |

兩份 Jenkinsfile 都以個人帳號 `yuxuan@192.168.60.6` 執行 `kubectl`，且含明文 registry 憑證——這是 infra / security 議題，本計劃只標記，不在此處理。

## 3. 不影響功能的工作原則（每張票都要套）

1. **變更分類**，決定驗證強度：
   - **A 純設定**（ConfigMap URL 換目標、清殘留 key）：staging 先改 → 對照 response → prod 改 → 觀察 → 保留舊值可一鍵回復。
   - **B 純基礎設施**（resources / HPA / probes / image pin）：不碰 code，觀察 p95 與 error rate。
   - **C code 但語意不變**（串行改並行、去中繼、request 內去重、cache）：必附 shadow diff（§3.4）+ 單元測試 + staging p95 前後比較。
   - **D 契約變更**（response 欄位、錯誤碼、端點移除）：**不在本計劃內**；若必要另開產品票，前端同步。
2. **先量測後動手**：沒有 Datadog p95 × volume 排名之前不挑端點；每張票寫下「改前 p95 / 改後目標 / 量測 query」。
3. **一次一件、一票一 PR、PR 開出後不再推 commit**（factory Git 紀律）；prod 影響變更 push 前 `npm run start:dev` 開機驗證 + 相關 spec 全綠。
4. **Shadow diff（仿 Core Migration 的 Shadow phase）**：對要改的端點，用 staging 真流量或錄製的請求集，同時打「舊版」與「新版」（同一 pod 內 feature flag 或兩個 deployment），JSON 正規化後比對（忽略時間戳、順序無關的陣列排序後比）。差異率 0 才准切。
5. **每個變更有 kill switch**：設定類保留舊 key；code 類用 env flag（比照 `GRPC_CLOUD_FALLBACK_ENABLED`）。
6. **並行化不得改變錯誤語意**：原本各自 try/catch 吞錯、回空值的下游，改成 `Promise.allSettled` 後仍各自吞；原本一個失敗整體 throw 的，用 `Promise.all`。要在票內明寫。
7. **不動 DB schema、不動 auth/ownership gate**（`trans-reports.controller.ts` 的 PHI ownership 檢查是 VP-17284 合規要求，任何「去中繼」都不能把它繞掉）。
8. **設定操作規範**：只用 `kubectl edit` / `kubectl patch` / dashboard，禁止 `kubectl apply -f` 本機 ConfigMap；改前先 `kubectl get cm -o yaml` 存檔。

## 4. Phases

> 順序建議：Phase 0 → 1 → 2，Phase 3 跟 VP-18152 節奏走，Phase 4 可與 1 並行，Phase 5 最後且需前端/PM 決策。每個 phase 開工前各出一份詳細 doc（本文件是總綱）。

### Phase 0 — 量測與防護網（不改任何行為）

目標：讓後面每一步都有「數字」和「自動化紅綠燈」。

| # | 工作 | 類別 | 產出 / DoD |
|---|---|---|---|
| 0.1 | ~~Datadog Top-20~~ → **已做（2026-09-11，subagent，`phase0-top20-endpoints.md` + appendix）**。資料源是 trace metrics（100% 請求，非 indexed spans 抽樣），7 天 09-04 ~ 09-11。Service 名：v1 `service:lis-trans-deployment env:prod`、v2 `service:lis-transv2-deployment env:prod`（`-st` 部署也打 env:prod，用 service 名排除）。p95 > 2 s 且 ≥ 100 hits 共 **11 支**（v1 REST 9、v1 gRPC 1、v2 GraphQL 1 = `PatientProfileSlow` 3,101 ms）。**高峰不是原因**：Top-10 的高峰 p95 與全週 p95 差在 ±5% 內，慢是結構性的。仍缺：常駐 dashboard（VP-18141 是 core 側的，trans 要自己一份）。 | 量測 | 完成（dashboard 待建） |
| 0.2 | 修 baseline 紅燈：v1 `npm ci`、兩 repo 的 stale mock（`createMetadataForCoresampleV2`、`createOAuth2Metadata`）、v2 `prisma.service.spec.ts` 改名為 `.integration.spec.ts` 或補 ignore。**v2 已完成（2026-09-14）**：main `be8344c` 10 紅 → 54/54 綠、731 pass，PR 見 §9；真正成因是 5 個 suite 在 import 時因缺 Kafka env 根本載不進來、其餘是 constructor 多了依賴而 spec 沒跟上。**v1 也已完成（2026-09-14，subagent）**：main `2d991af` 16 紅 → 58/58 綠、716 pass；真正成因是 9 個 CLI 骨架 spec 零 provider、`redis.ts`/`redis_s.ts` import 時就連真 Redis（改用 jest setupFiles 全域 stub）、以及多個 spec 停在舊 contract（`createMetadatav3`、舊 getTimeLine 形狀、AppModule 直接 import）。PR 見 §9 | C（僅測試碼） | 兩 repo `npm test` 全綠（可接受少數標記 skip 並開票） |
| 0.3 | CI gate：兩 repo 的 deploy workflow 加 `npm ci` + `tsc --noEmit` + `jest --ci` job，紅燈不 build image | 流程 | PR 到各 repo；**這是 automation 行為變更，走 PR 不直推** |
| 0.4 | 契約快照：v1 Swagger JSON、v2 `schema.gql` 由 CI 產生並 diff（新增允許、刪除/型別變更 fail） | 流程 | 快照檔入 repo |
| 0.5 | ConfigMap 基線與 drift 偵測：把 4 個 ConfigMap（prod/st × v1/v2）去 secret 後存檔（Appendix B 即第一版）；腳本每日 diff cluster vs 基線並通知 | A | 腳本 + 團隊規範（§3.8）公告 |
| 0.6 | 請求錄製 / 重放工具（shadow diff 的基礎）：對 Top-20 端點在 staging 錄一組去 PHI 的請求集，寫 diff 腳本 | 工具 | 能對任一端點跑 old vs new 比對 |
| 0.7 | k6 負載腳本針對 Top-20，staging 可重複跑出 p95 | 工具 | baseline 數字入 doc |

風險：幾乎為零（不碰 prod 行為）。相依：Datadog 權限（Leo 帳號）。

### Phase 1 — 設定層去套娃與去回繞（A 類為主，少量 C）

| # | 工作 | 類別 | 驗證 | 回滾 |
|---|---|---|---|---|
| 1.1 | S1：transv2 `checkIfPersonalizedReportCanBeCreated` 從 cloud-local-proxy 改直指 `http://192.168.60.77:8081/secure/nologin/CheckIfPersonalizedReportCanBeCreated?sampleId=`（與 v1 prod 值一致）。**2026-09-14 完成（st 11:25、prod 11:40 PT）**：config-only，runbook `phase1-s1-runbook.md`、腳本 `scripts/phase1-s1-repoint.sh`。等價證據：prod pod 內舊路 vs 新路逐一比對 58 個真實 sample（38 `false` + 20 `true`）status/body 全同，非數字 id 兩邊皆 500（v2 端一律 null）；on-prem 對 Authorization header 不敏感；單跳 avg 73 → 41 ms。備份在 `~/.trans-opt-backups/`（含 secret，不入 repo） | A | staging → 比對 → prod（已做） | `scripts/phase1-s1-repoint.sh <st\|prod> --rollback`（還原備份值 + rollout restart） |
| 1.2 | S6 / S7：清 v1 14 個、v2 8 個「0 處讀取」的殘留 key | A | grep 確認 0 read（已做）；staging 先刪、跑一輪 smoke | 從基線檔還原 |
| 1.3 | S8：v1 公網回繞改 in-cluster svc DNS。分批（每個目標服務一批）：base-report → shipping → accounting/charging → samples → interactive-report → 其他。**每批先確認**：(a) 目標服務有 in-cluster svc（v2 的 CM 已給出對應值可直接沿用）；(b) 公網 ingress 是否注入 header / 做 auth（in-cluster 打不到就會 401）；(c) http vs https 差異 | A | staging 先；Datadog 比對該端點 p95 與 error rate；shadow diff | 換回公網 URL |
| 1.4 | S2：transv2 對 `proxy_getkit` / `proxy_getteststatus` / `proxy_getQuestionaire` 改為直接用 v2 自己的 gRPC client（邏輯以 v1 `src/proxy/proxy.service.ts` 為準，逐行對照搬移）。**2026-09-14 code 完成，PR #629**（runbook `phase1-s2-runbook.md`）：`TRANS_PROXY_GRPC_MODE` = http（預設，零變更）/ shadow（雙路 + `proxy_grpc_shadow` log）/ grpc；merge 後先 shadow 24 h 看 equal 100% 再切 | C | shadow 在 prod 全量流量上比對（customer-agnostic），equal 必須 100% | ConfigMap 改回 `http` + rollout restart |
| 1.5 | S3 / S4 / S5：`getSetting*`、`va_events`、`skin_placepatientorders` 逐一評估「v2 能否等價重現」。**預設保留**（v1 `getSetting` 聚合邏輯重，重現風險高），只做兩件低風險事：確認值已是 in-cluster（是）、加 timeout 與 Sentry 分類 | 評估 | 各出一頁分析 | — |
| 1.6 | cloud-local-proxy 退役（**路由已全部在 trans v1 有等價實作**，見 §2.9）：(a) 向 infra / Ray 要雲上 `api.vibrant-america.com/v1/lis/cloud-proxy` 與地上 `www.vibrant-america.com/lisapi/v1/lis/cloud-proxy` 兩個 ingress 的 access log，列出所有 caller 與路由；(b) 已知 caller 改指向：transv2 S1 → 1.1；`LIS-backend-billing` `sendSkinPlacePatientOrders` → trans v1 `/proxy/grpc/sendSkinPlacePatientOrders`（需 billing 側一張票，JWT 由 trans 的 `CustomJwtAuthGuard` 驗）；(c) 未知 caller 逐一處理；(d) 兩個集群的流量歸零 30 天後 scale-to-0（雲上 `cloud-local` ns 由 AKS 權限者做；地上 `lis` ns 由 Ray / appserver05 做），再 archive repo | 調查 + A | ingress log 顯示 0 request | scale 回原 replicas |
| 1.7 | cloud-local-proxy 在退役前若還要改（Ray 已 unarchive）：**不投資新功能**，最多只做 SHA-pin image + probes；任何路由修正一律改在 trans v1 的等價端點 | 原則 | — | — |

### Phase 2 — 熱點端點並行化 / 去重（C 類，語意不變）

以 Phase 0.1 的 Top-20 為準，每端點一票。手法限定四種，不做重寫：

1. **串行 → 並行**：彼此無資料相依的 await 改 `Promise.all` / `allSettled`（依原錯誤語意）。
2. **N+1 → batch**：for-loop 內的 RPC 改成既有 batch API（如 `getReportStatusListV2Batch`、`listpatients`）；沒有 batch API 就不做（不擅自改下游）。
3. **request 內去重**：同一請求對同一 key 的重複下游呼叫（如 patientProfile 對同 sample 打 `proxy_getkit` 4 次）以 request-scoped memo 合併。
4. **短 TTL cache**：只對已有 redis cache pattern 的端點調 TTL 或補 cache；不對寫入路徑加 cache。

**實測排名（Phase 0.1，p95 × hits，7 天，排除 OPTIONS / health）與對應手法**：

| # | 端點 | hits/7d | p50 / p95 / p99 (ms) | 時間花在哪（trace） | 手法 |
|---|---|---|---|---|---|
| 1 | v2 `POST /graphql`（全部 operation） | 119,413 | 203 / 1,568 / 2,656 | 最慢 operation：`PatientProfileSlow` p95 3,101、`PatientProfileFast` 1,918、`PatientPNS` 1,747。**2026-09-14 實測修正**：`PatientProfileSlow` 只選 `order` + `sample_with_questionnaire_report` 兩個 field；後者對每個 sample 用一個 `Promise.all` 同時打 14 個下游，wall time = 最慢那支。7 天 transv2 outbound p95：shipping `/orders/samples/horm-qnr/status` **2.7 s**（p50 1.2 s）、interactive-report `/questions-data/getBarcodeQuestionnairesStatus` **1.9 s**、三支 zoomer-qnr 各 1.1 s；S2 三跳只有 0.25–0.52 s 且並行 → **拔掉 S2 對這支 p95 幾乎無效**。代表 trace `6aa840e3…`（3.8 s）：horm-qnr 3.42 s、getBarcodeQuestionnairesStatus 3.65 s，其餘全部 < 0.5 s。Redis GET p95 10 ms（trace 內 1 s 那筆是 max 2 s 的極端值） | trans 側能做的有限：samples 迴圈由串行改並行（多 sample accession 才有感）、request-scoped memo；根治在 shipping / interactive-report 的那兩支 API（跨團隊）。1.4（S2 直連）仍值得做但定位為去套娃，不是 p95 手段 |
| 2 | v1 `GET /dashboard/user/timeline` | 46,845 | 1,568 / 2,915 / 4,295 | 2.6 s 在下游 lis-dashboard `UserTimelineFetch` | **跨團隊**：計畫原本沒列；trans 側只能加 timeout / cache，根治在 dashboard 服務 |
| 3 | v1 `GET /utility/getSetting` | 310,636（v1 有效流量 38%） | 190 / 333 / 1,831 | 固定 9 支 core gRPC；p99 時 9 支同時卡 ~1.5 s 而 core 自身下游只 0.3 s → 瓶頸疑在 trans→core 這一跳（連線 / channel）。又被 PDF、lis-order 回頭呼叫（一份 PDF 打 4 次 → 37 支 core gRPC），是**放大器** | 4（cache）+ 1（9 支並行）+ 查 gRPC channel 設定 |
| 4 | v1 `POST /trans/findPatient` | 29,189 | 1,016 / 2,826 / 5,254 | ~~14 次 core gRPC + 經 HTTP 打自己~~ → **2026-09-14 實讀更正**（`phase2-findpatient-analysis.md`）：current main 對 core 是 9 個 gRPC（Stage A 5 個並行 + `GetSampleReceiveRecords` ×3 + `GetSampleTests`），**沒有**自打 `/utility/GetSampleInfo`（src 無引用、Datadog 0 筆）。真正瓶頸是 Stage A 之後 B→C(getEstimateTimev3)→D(getIssue)→E(getPatientIssue)→F(FedEx)→G→H 全部串行約 1.36 s，而 C、D、E 零資料依賴、各自內部 catch | 1（C ∥ (D→F) ∥ E，估 p95 2.8→~2.1 s）、`GetSampleTests` 併入第一波、metadata 一次建、`get_issue_id(12)` 用既有 `BatchGetIssuesByObjectIds`。**先補 golden-response spec 再動** → **2026-09-14 已做：PR #769**（golden spec 21 tests + P1 + P2；p95 預估 2.8→~2.1 s，待 release 後量） |
| 5 | v1 `GET /proxy/old-report/downloadTestOrderPDF`（及另兩支 PDF，p95 11 ~ 14 s） | 7,284 | 6,629 / 11,230 / 13,738 | 時間在 lis-order / pdf-engine，trans 只是 proxy；**trace 顯示 pdf-engine 的 peer 是 `lis-shipping-deployment-staging`，要確認 prod 是否打到 staging** | Phase 5 退場候選；先查 staging peer |
| 6 | v1 `GET /trans/patientTestResultnewrange` | 7,335 | — / 6,135 / — ，err 1.87% | 一次請求對 core `GetPatientDetailedReferenceRangeInOut` 打 **365 次**（就是 `getDetailRangeInfo*` 的 N+1） | 2（batch rpc，需 core 提供）|
| — | v1 `getTimeLine` | 見 appendix | — | 經 HTTP 打自己 `/trans/patientTestKitInfo` | 1、去除自己打自己 |
| — | 公網回繞 | — | 單次 0.8 ~ 3.8 s | `api.vibrant-wellness.com` → lis-base-report | = Phase 1.3（S8），優先做 base-report 那批 |

三個結構性成因：對 core 的 N+1 gRPC、公網回繞、trans 經 HTTP 打自己。`getTubeInfo*` / `getDetailRangeInfo*` 不是公開端點，是內部函式，故不在排名裡。

DoD（每票）：shadow diff 0 差異；spec 覆蓋新分支；staging p95 下降且 error rate 不升；prod 觀察 7 天。

**2026-09-14 Phase 2 進度（Leo：「能修的直接修」）**

| 端點 | 實讀結論 | 動作 | 狀態 |
|---|---|---|---|
| v1 `findPatient` | 串行 pipeline，非 N+1、無自打 | P1 並行 + P2 GetSampleTests 提前 | **上線**（#769）；改後 47 min p50 0.92 / p95 0.94 s（低流量時段，待工作日再量） |
| v1 `patientTestResultnewrange` | 365 gRPC 已並行（~1.5 s）；串行的是 `full_test_mapping` HTTP（3–4.5 s） | 提前發送、原位 await；兩個報告 GET 併行 | PR #775 |
| v1 `createPatient` | p50 3.8 s 中 ~2.9 s 是每則 Kafka 訊息各自 connect/disconnect（14 則） | 長駐 producer（同 record、同順序） | PR #773 |
| v1 `getTimeLine` | `serviceToken` 卡住整個 Promise.all；invoice/fallback 串行走公網；kits 呼叫繞公網→LIS-Sample→打回 trans v1（p50 1.39 s） | A-PR1 排程重整 | PR #774；A-PR2（kits 改內部 + shadow）進行中 |
| v1 `updatePatient` | ~全部在 core `UpdatePatientInformantWithWriteBack` | 不動 | — |
| v1 gRPC `GetSampleInfo` | p95 在 core `GetSampleTests` cache miss（3.2 s） | 不動 | — |
| v2 `PatientProfileSlow` | 尾巴在 shipping / interactive-report | 不動（跨團隊） | — |
| PDF ×3、dashboard timeline | 時間在 lis-order / pdf-engine / lis-dashboard | 不動（跨團隊） | — |

分析報告：`phase2-findpatient-analysis.md`、`phase2-newrange-analysis.md`、`phase2-timeline-sampleinfo-analysis.md`、`phase2-create-update-patient-analysis.md`。每個 code PR 都先有 golden-response spec 或等價的既有 spec 當安全網。

### Phase 3 — 配合 Core v1 退役（VP-17348 Phase 4 / 4b；trans 側的票是 VP-18152）

> v0.3（2026-09-11）依 Jira 實讀改寫。原 v0.1 提的「自建 CoreClientProvider + CORE_TARGET flag + trans 側 shadow」**撤回**：Core 團隊的做法是在 **server 端**做切換（V1 gRPC reverse-proxy 到 V2、per-function、由他們的 shadow 框架驅動），caller 完全不用改。trans 若自建一套切換與 shadow，會跟 VP-18122 ~ VP-18130 重工，還會踩到 epic 明列的最高風險「proto freeze 是長期硬依賴」。

**Core epic 的實際結構（Appendix C）**

| Core 側 phase | 內容 | 對 trans 的意義 |
|---|---|---|
| Phase 4 Read cutover（VP-18122 ~ 18130，9 張，全部 Dev To Do） | V1 gRPC 對 V2 做 reverse proxy，per function、可逐個回退；target 9 月底 | **trans 不用動 gRPC client**。trans v2 那 20 處 `SERVER_ENVIRONMENT==='prod' \|\| FORCE_CORE_V1_STAGING` 在 prod 走 v1 gRPC，v1 會自己轉到 v2。**嚴禁**在此期間改動 trans vendored 的 core proto（v1 `protos/lis_main.proto` 與 `protos/coresamplev2/`；v2 `protos/`、`protos2/`）——proto 分歧會讓 proxy 失效 |
| Phase 4b Core v1 REST Retirement（VP-18140 ~ 18157，Sprint 28） | 344 條 core v1 HTTP 路由，只有 19 條 30 天內有流量；P0 log probe → P1 補 v2 缺口 → P2 前端/死碼 → **P3 殘餘 caller 改走 v2（含 VP-18152 trans）** → P4 刪 HTTP（10-31）→ P5 關 ingress（11-15） | **VP-18152 的 scope 只有一句：trans 不再用 core v1 HTTP。** 對應本文 §2.3 的 4 個殘留呼叫 |
| Phase 5 Write migration | 尚未拆票，target dev complete 09-25 | trans 的 `create_patient` / `create_patientv2` 是**寫**，落在這裡 |
| Phase 6 V1 deprecation | GA target 09-28，但 reverse proxy 拆掉前 V1 不能退 | 那 20 處切換點的清理時機 = V1 真正退役時，且是「刪掉 v1 分支」而不是加 flag |

**VP-18152（Zhibin，Dev To Do，P2，target 09-30，QA twin QH-7030）**
- 相依：VP-18140（core v1 HTTP 全域 request log，**已於 09-10 上 staging + prod**，Datadog query `@event:core_v1_http_request`，欄位含 `route / user_agent / jwt_sub / x_forwarded_for`）與 VP-18142（v2 補 `UpdatePatientInformantWithWriteBack`，Dev To Do；受益者是 LIS-Shipping / LIS-Sample / order-management，**不是 trans**——所以 trans 這張其實只被 VP-18140 卡）。
- trans 側要處理的 4 個呼叫（§2.3）與對應 v2 rpc：

| 呼叫點 | core v1 HTTP 路由 | 讀/寫 | v2 對應 | 備註 |
|---|---|---|---|---|
| v1 `setting.practiceInfo.service.ts:9036`、v2 `setting/setting.service.ts:1562` | `/api/clinic/list-customer-by-id/:clinic_id` | 讀 | `ListClinicCustomersByClinicID` | 這支是 VP-18144「7 個零流量 v2 rpc」之一，Fan 正在 shadow（Dev In Progress）。**要等 VP-18144 對這支收斂才能切** |
| v1 `utility/utility.service.ts:8131` | `/api/patient/create-patient` | 寫 | 待確認（Phase 5 未拆票） | 兩支 create 都要先確認 v2 `PatientService` 有等價 rpc 且 write-back 行為一致 |
| v1 `utility/utility.service.ts:8339` | `/api/patient/create-patient-new` | 寫 | 待確認 | 同上；另帶 `create_patientv2_token` 的 Bearer，改 gRPC 後 auth 方式會變 |

- 09-10 VP-18140 上線後的早期觀察（Zhibin 留言）：HTTP caller 全部沒送 service-name header，只能靠 `user_agent + jwt_sub` 歸因；trans 的 axios 呼叫會被歸為 "an axios client"。**Phase 3 第一個動作是用這個 log 證實我們的 4 個呼叫點在 prod 的實際流量**（可能其中幾個已經是零）。

**trans 側工作項（Phase 3 重寫）**

| # | 工作 | 類別 | 相依 / 驗證 |
|---|---|---|---|
| 3.1 | ~~用 `@event:core_v1_http_request` 查 trans 4 個呼叫點流量~~ → **已做（2026-09-11，subagent，報告 `phase3-core-v1-http-traffic.md`）**。Prod 窗口 09-10 19:22Z ~ 09-11 23:12Z（27.9h，n=58,110）：`list-customer-by-id` 從 trans v1 448 次、trans v2 19 次（每天都有，**活的**，APM p95 約 300 ms）；`create-patient` 0、`create-patient-new` 0、`login_via_session` 0。但 create 兩支都在 `createPatientBatch`（v1 `utility.service.ts:8057`）這條**批次路徑**，27.9h 看不到不等於死，10-01 後要重跑。**最大發現：VP-18156 真正的 blocker 是 lis-order（Java），佔 91% 的 core v1 HTTP 流量、`list-customer-by-id` 一天約 9k 次**；trans 遷完也刪不了這條路由。另：log 的 `jwt_sub` 全為空字串（疑 middleware 讀錯 claim），已建議回饋 VP-18140。 | 量測 | 完成 |
| 3.2 | `list_customer_by_id_carlos`（v1 + v2 各 1 處）→ `ListClinicCustomersByClinicID` gRPC；response mapping 對照 v1 HTTP 回傳 shape，shadow diff 零差異 | C | **等 VP-18144 對該 rpc 收斂**；v2 可直接用既有 `coresamplev2` client |
| 3.3 | `create_patient` / `create_patientv2` → v2 gRPC：先向 Zhibin 確認 v2 有無等價 create rpc、是否在 Phase 5 拆票；沒有就開一張 P1 補缺口票（比照 VP-18142） | C + 相依 | 寫路徑，需 staging 真實建 patient 比對 DB row |
| 3.4 | 刪 v1 `trans.grpc.options.ts:142-147` dead code（`coreSampleV2Url`），順手把 v1/v2 core gRPC client 的 keepalive / timeout 設定對齊 | C（無語意） | tsc + start:dev |
| 3.5 | **不做**：CoreClientProvider / CORE_TARGET flag / trans 側 shadow（撤回，理由見上） | — | — |
| 3.6 | 那 20 處 `FORCE_CORE_V1_STAGING` 切換點：Phase 6 V1 退役後一次刪掉 v1 分支；在此之前只在「本來就要改該檔案」時順手收斂，不單獨開票 | 延後 | 跟 Core Phase 6 |
| 3.7 | Proto freeze 紀律：本計劃期間任何要動 trans vendored core proto 的變更，先問 Core 團隊；VP-17748 那種「consumer sync」只能在 core 兩邊都 live 後做 | 原則 | — |

**時程約束**：P3 target 09-30、P4 刪 HTTP 10-31。trans 的 4 個呼叫必須在 10-31 前改完，否則 create-patient 那兩支會直接 404。

**相關但不屬本計劃的 Core 側票**：VP-18143（`multi_login_test` 的 impersonation auth 要搬進 trans，Fan，Dev Complete 09-11）——**trans 會新增一個端點**，需確認它落在 v1 還是 v2、有沒有走既有的 auth guard；VP-18155（`getQuestionnaireRequiredMap` 的 self-owned caller → v2，Fan）——trans v1 讀 `getQuestionnaireRequiredMap` 5 處但目標是 lis-order 不是 core，先確認該票是否把 trans 算進去。

### Phase 4 — 基礎設施與韌性（B 類，可與 Phase 1 並行）

- resources：補 CPU requests 與 memory/CPU limits（先用 Datadog 觀測值的 p99 × 1.5）；再上 HPA（CPU 70%，min 3 / max 6）。
- v1 `LoggingInterceptor`：response body 改為只記 size + 前 N bytes 或關閉（PHI + CPU）；request body 同。**這是行為變更（log 內容），需 Leo 同意；不影響 API 回應。**
- gRPC channel 設定統一（v1 `lis` client 有 30s timeout，v2 沒有；keepalive 參數兩邊不同）。
- cloud-local-proxy：若暫不退役，至少 SHA-pin image + 加 probes（infra 負責）。
- Node 版本對齊（v1 22 / v2 20）：低優先。

### Phase 5 — 純轉發端點退場（需前端 + PM 決策）

盤點對象：v1 `trans-reports.controller.ts`（19 routes）、`proxy/old-report`（11）、`proxy/grpc`（6）。分三類處理：

1. **有 PHI ownership gate**（VP-17284 系列）：保留在 Trans，或把 gate 搬進目標服務後再退——不可直接讓前端直打。
2. **純轉發、無 gate、無聚合**：前端改直打目標服務（需前端票），Trans 端先加 deprecation log，流量歸零 30 天後移除。
3. **Trans gRPC `TransService` 5 methods**：有 3 個消費者，**不在退場範圍**。

**Track W — web-homepage-api（`vw-page`）的去向**（需 Leo / PM / report 團隊決定，本計劃只給選項）：

| 選項 | 內容 | 代價 | 建議 |
|---|---|---|---|
| W0 保留原地，補管線 | 不併入 trans；補 CI（lint + 至少 smoke test）、把 Jenkins 的個人帳號 ssh 部署換成正式 pipeline、image SHA-pin | 最小；不動任何功能 | **短期一定要做**（不論 W1 / W2） |
| W1 只搬 report action 三條 | `getAllReportActions` / `getIndividualReportCount` / `createReportActions` 搬到 trans v2（REST），資料層需決定：續用 Mongo（trans 新增 Mongo client，不建議）或改存 MySQL / PG 並做一次性遷移；三個前端改 base URL；HMAC 驗證換 JWT | 中；有資料遷移與前端改動 | 可做，但要等 Phase 0 防護網完成，且與 report 團隊確認這三條的 owner |
| W2 整包併入 trans | 72 條官網 CMS 路由 + Mongo + HubSpot / Postmark 全搬 | 高；把行銷官網後端塞進 PHI gateway，違反 trans 的定位（§1） | **不建議** |

> 結論：web-homepage-api 與 trans 的交集只有 report action；「昊哥要下掉併進 trans」在盤點後建議收斂成 W0 + 視需要 W1。

## 5. 風險與回滾總表

| 風險 | 影響 | 緩解 |
|---|---|---|
| in-cluster 直連後遇到 ingress 才有的 auth/header/TLS 行為 | 該端點 401/500 | 每批先在 staging 驗；保留公網 URL 一鍵回復 |
| 並行化改變錯誤語意（原本吞錯 → 現在整體 throw） | 前端看到新錯誤 | §3.6；spec 明寫失敗分支 |
| ConfigMap 被他人 apply 覆蓋 | 前面的 A 類變更被回滾 | Phase 0.5 drift 偵測 + 規範 |
| Jira 內容未讀（VP-18152 等） | 與 core 側重工或衝突 | Jira 恢復後先讀再開 Phase 3 |
| 測試基線紅 | 無法證明「不影響」 | Phase 0.2/0.3 先做完才進 Phase 2 |
| cloud-local-proxy 有未知 caller | 退役造成別的服務斷 | Phase 1.6 只調查，不 scale-to-0 |

## 6. 建議的票（草稿，英文標題，尚未建）

- `[Trans Opt][P0] Datadog p95 x volume dashboard for trans v1/v2 and Top-20 slow endpoint list`
- `[Trans Opt][P0] Restore green test baseline in LIS-transformer and LIS-transformer-v2`
- `[Trans Opt][P0] Add test/typecheck gate to deploy workflows (both repos)`
- `[Trans Opt][P0] Contract snapshots: Swagger (v1) and schema.gql (v2) diff in CI`
- `[Trans Opt][P0] ConfigMap baseline + drift detection for lis-trans-config / lis-transv2-config`
- `[Trans Opt][P1] transv2: point checkIfPersonalizedReportCanBeCreated directly at the report server (bypass cloud-local-proxy)`
- `[Trans Opt][P1] Remove unread cloud-proxy config keys (14 in v1, 8 in v2)`
- `[Trans Opt][P1] trans v1: replace public-ingress URLs with in-cluster service DNS (batched by target service)`
- `[Trans Opt][P1] transv2: replace proxy_getkit/getteststatus/getQuestionaire HTTP hops with direct gRPC`
- `[Trans Opt][P1] Inventory all callers of cloud-local-proxy via ingress access logs (cloud + on-prem)`
- `[Trans Opt][P1] LIS-backend-billing: repoint sendSkinPlacePatientOrders from cloud-proxy to trans v1 /proxy/grpc`
- `[Trans Opt][P1] Retire cloud-local-proxy: scale-to-0 in AKS cloud-local and on-prem lis after 30 days of zero traffic`
- `[Trans Opt][P1] web-homepage-api: add CI (lint + smoke) and replace personal-account ssh deploy; pin image`
- `[Trans Opt][P5][decision] web-homepage-api report-action endpoints: keep (W0) vs move to trans v2 (W1)`
- `[Trans Opt][P2] <one ticket per Top-20 endpoint>: parallelize / dedupe without behavior change`
- `[Trans Opt][P3] Measure trans's 4 core v1 HTTP call sites with the VP-18140 request log (@event:core_v1_http_request)` (subtask of VP-18152)
- `[Trans Opt][P3] list_customer_by_id_carlos -> ListClinicCustomersByClinicID gRPC in trans v1 + v2` (subtask of VP-18152; blocked by VP-18144 convergence)
- `[Trans Opt][P3] create_patient / create_patientv2 -> core v2 gRPC` (subtask of VP-18152; needs a v2 create rpc confirmed or a P1 gap ticket)
- `[Trans Opt][P3] trans v1: remove dead coreSampleV2Url + align core gRPC channel settings`
- ~~CoreClientProvider / CORE_TARGET flag~~ withdrawn (Core does server-side reverse proxy, VP-18122~18130)
- `[Trans Opt][P4] Resource requests/limits + HPA for lis-trans / lis-transv2`
- `[Trans Opt][P4] trans v1 LoggingInterceptor: stop serializing full request/response bodies`

## 7. 需要 Leo 決定 / 補的事

1. **文件歸屬**：本計劃目前在 personal repo `docs/plans/trans-optimization/`。若要當 wave doc 走 `agent-waves`，本機兩個候選路徑都不存在，需要 clone。
2. ~~Jira~~ → 已用 Jira REST（agent `.env` 憑證）讀完 VP-17348 及 P0 ~ P5 子票，Phase 3 已依實讀改寫（v0.3）。MCP 對本 session 仍失效：`claude mcp list` 顯示 Atlassian Connected，但已啟動的 session 不回填工具清單；新 session 即可。`vibrant` MCP 需在 CLI 按一次 approve。
3. **Phase 順序與人力**：建議 Phase 0 全部先做（約 1 個 sprint，不碰 prod 行為），再開 Phase 1。Phase 3 的節奏跟 Zhibin 的 VP-18152。
4. ~~`LoggingInterceptor` 改 log 內容算不算影響功能~~ → **已拍板：不算**（Leo 2026-09-11）。
5. **cloud-local-proxy 的 ingress access log**（雲上 `api.vibrant-america.com/v1/lis/cloud-proxy`、地上 `www.vibrant-america.com/lisapi/v1/lis/cloud-proxy`）由誰拉；地上集群我沒有存取權，Ray 有（appserver05）。
6. ~~Datadog 存取~~ → 已解：Leo 2026-09-11 給了內部 `vibrant` MCP（`192.168.60.8:8800`，Vibrant MCP Server 3.2.4）的 bearer token，該 server 提供 Datadog / Sentry / Jira / Zendesk / sample-events / audit-log 工具。token 存 working-agent `.env`（`VIBRANT_MCP_TOKEN`，gitignored）；MCP header 設在 local scope（`~/.claude.json`），**未動** repo 內共享的 `.mcp.json`。新 session 起可直接用；本 session 可用 curl 直呼。
7. **web-homepage-api 去向**（Track W）：W0 一定做；W1 是否做、誰是 report action 的 owner，需 report 團隊（Yekai / Yuteng）與 PM 決定。
8. **`LIS-backend-billing` 的 cloud-proxy 呼叫**要開票給 billing 團隊改指向；在那之前地上的 cloud-local-proxy 不能 scale-to-0。我對該 repo 沒有寫入權（push 403），註解以 patch 檔提供。
9. ~~D12 draft PR~~ → 已開三個（#752 / #626 / #20）；billing 不處理（Leo 2026-09-11）。

## 9. 協作入口（2026-09-11 第一步已完成）

所有「緊急要改」的 code 位置都已加上 grep-able 註解 **`TRANS-OPT`**，只有註解、零行為變更，各 repo 一個 branch `feature/leo/TRANS-OPT`：

| repo | commit | 狀態 | 標記位置 |
|---|---|---|---|
| LIS-transformer | `aa9da9c` | 已 push；draft PR #752 https://github.com/Vibrant-America/LIS-transformer/pull/752 | `trans.grpc.options.ts`（dead code）、`logging.interceptor.ts`（P4）、`utility.service.ts:8131,8339` + `setting.practiceInfo.service.ts:9036`（core v1 HTTP） |
| LIS-transformer-v2 | `655ba73` | 已 push；draft PR #626 https://github.com/Vibrant-America/LIS-transformer-v2/pull/626 | S1 `patientProfile.resolver.ts`、S2 `patientProfile.service.ts` ×5 + `utility/utility.service.ts:2577`、S5 `utility.service.ts:3277,3330`、S3 `PNS.service.ts:405` + `PNSResolver.resolver.ts:316`、S4 `utility.api.service.ts:2340`、core v1 HTTP `setting/setting.service.ts:1562` |
| cloud-local-proxy | `888f37f` | 已 push；draft PR #20 https://github.com/Vibrant-America/cloud-local-proxy/pull/20 | 兩個 controller 頂端 RETIRING 註解 |
| LIS-backend-billing | `12828a4`（本機） | **push 403，我只有 pull 權限**；patch 在 `patches/LIS-backend-billing-TRANS-OPT-annotation.patch`。注意該 repo 預設分支是 `cloudproduction`，同一行在該分支也存在 | `ProZOrderServiceImpl.java:115` |

搜尋方式：`grep -rn "TRANS-OPT" src`。每則註解含分類標籤（`[P1-S1]` … `[P4]`、`RETIRING`）、該做什麼、以及不能做什麼。三個 draft PR 已開（Leo 2026-09-11 拍板 D12）；billing 依 Leo 指示不處理。

Phase 3 的 20 個 core v1/v2 切換點**沒有**標，因為不屬「緊急」；要標的話一行 sed 可以補。

## 8. 附錄索引

- Appendix A：會議轉錄摘要（`appendix-a-transcript-summary.md`），原始逐段轉錄在 `raw-transcript/`（p1_00 ~ p1_04 為第一段每 5 分鐘一檔，p2_00 ~ p2_01 為第二段）。
- Phase 0.1 報告：`phase0-top20-endpoints.md` + `phase0-top20-endpoints-appendix.md`（subagent，2026-09-11）。
- Phase 3.1 報告：`phase3-core-v1-http-traffic.md`（subagent，2026-09-11）。
- Phase 1.4 runbook：`phase1-s2-runbook.md`（2026-09-14，PR #629 待 review）。
- Phase 2 findPatient 分析：`phase2-findpatient-analysis.md`（2026-09-14，subagent，唯讀分析 + PR 順序）。
- Phase 1.1 runbook：`phase1-s1-runbook.md` + `scripts/phase1-s1-repoint.sh`（2026-09-14 已執行 st + prod；含執行紀錄與 after 驗證）。
- Appendix C：VP-17348 epic 與 Core v1 REST Retirement 子票全文 dump（`appendix-c-jira-vp17348.md`）。
- Appendix B：AKS 唯讀盤點（`appendix-b-k8s-inventory.md`）：4 個 ConfigMap 的 URL key 分桶、cloud-local-proxy 前面擋的目標、4 個 deployment 的 replicas / resources / probes。
- 證據檔位（repo 內）：
  - v1 core/gRPC client：`LIS-transformer/src/trans/trans.grpc.options.ts`
  - v1 proxy 模組：`LIS-transformer/src/proxy/{proxy,old-report}.{controller,service}.ts`；遷移說明 `LIS-transformer/docs/proxy-migration-configmap.md`
  - v1 findPatient：`LIS-transformer/src/trans/trans-patient-search.controller.ts:211`、`getPatient.service.ts:369-1166`
  - v1 logging：`LIS-transformer/src/logging.interceptor.ts`
  - v2 core 切換點：見 §2.3 列表；cloud fallback：`LIS-transformer-v2/src/calendar/shared/with-cloud-fallback.util.ts`
  - v2 套娃讀取點：`patientProfile.resolver.ts:335`、`patientProfile.service.ts:725,976,1553,1568,1613`、`utility.service.ts:2577,3277,3330`、`PNS.service.ts:405`、`PNSResolver.resolver.ts:316,320`、`utility.api.service.ts:2340`
  - CI：`LIS-transformer/.github/workflows/deploy-prod.yml`、`LIS-transformer-v2/.github/workflows/frontend-service-graphql.yml`
  - cloud-local-proxy：`cloud-local-proxy/src/grpc/grpc.controller.ts`、`src/old-report/old-report.controller.ts`、`jenkins/Jenkinsfile`
  - web-homepage-api：`web-homepage-api/src/endpoints/webpage.py`（report action 於 L835-900）、`src/core/report_action.py`、`src/api.py:81-82`、`jenkins/Jenkinsfile`
  - 外部 caller：`LIS-backend-billing/.../ProZOrderServiceImpl.java:115`、`va-portal/src/views/PatientProfilePage/service/UserActionService.js:6-7`、`report-pdf/src/service/UserActionService.js:6-7`、`ehr-frontend/src/services/report/report-service.js:38-39`
