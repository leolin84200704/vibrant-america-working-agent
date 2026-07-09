---
id: repos
type: ltm
category: technical
status: active
score: 0.9356
base_weight: 0.9
created: 2026-04-22
updated: 2026-04-22
links:
- INCIDENT-20260518
- INCIDENT-20260528
- INCIDENT-20260601-sftp-hang
- INCIDENT-20260604
- LBS-1487
- LBS-1547
- PO-222
- QH-1104
- QH-1130
- QH-1159
- QH-1591
- QH-1775
- QH-1860
- QH-211
- QH-2259
- QH-2648
- QH-680
- QH-862
- QH-918
- QH-919
- VP-15460
- VP-16009
- VP-16154
- VP-16164
- VP-16165
- VP-16168
- VP-16169
- VP-16172
- VP-16232
- VP-16337
- VP-16361
- VP-16391
- VP-16410
- VP-16499
- VP-16512
- VP-16513
- VP-16514
- VP-16516
- VP-16520
- VP-16521
- VP-16612
- VP-16629
- VP-16664
- VP-16689
- VP-16759
- VP-16760
- VP-16784
- VP-16785
- VP-16786
- VP-16787
- VP-16850
- VP-16859
- VP-16921
- VP-16945
- VP-16954
- VP-16955
- VP-16968
- VP-16980
- VP-17065
- VP-17077
- VP-17217
- VP-17222
- VP-17312
- business-model
- business-model-deep
- failures
- repo-catalog
tags:
- repos
- nestjs
- prisma
- grpc
summary: 'Active repo reference: tech stack, ports, key areas, setup'
---
































































































# Repo Reference

> Quick reference for each repo. Read repo source code directly for detailed structure.
> **全公司 repo 服務地圖（每個 repo 是什麼、本質、在生態系的角色）見 `repo-catalog.md`** — 本檔只放正在開發中 repo 的深度 operational gotcha；不在下方清單的 repo（v2 財務微服務、LIS-Sample/Shipping/Lab-test、OAuth/RBAC、各前端 portal、legacy 服務等）到 catalog 查。

---

## Active Repos

### LIS-transformer-v2
- **Purpose**: LIS frontend GraphQL API gateway
- **Tech**: NestJS 11, TypeScript, Prisma (PostgreSQL + MySQL dual schema)
- **Port**: 3390
- **Key Areas**: `src/trans/` (orders/patients), `src/calendar/`, `src/setting/`, `src/questionnaire/`
- **Setup**: `npx prisma generate` for both schemas, then `npm run start:dev`
- **Migration scripts**: `scripts/` 目錄（standalone ts-node）或 `src/calendar/migration/`（NestJS service，但 gRPC 不可用）
- **Clinical Consult (practice_id=150105) 關鍵檔案**:
  - `src/calendar/models/event/event.service.ts` — `createEvent` (L436-641) / `createEventByPatient` (L1255-1582) / `updateEventByPatient` (L1619+) / `deleteEventByPatient` (L1775+) / `sendAppointmentScheduledEmail*` (L3922-4181)
  - `src/calendar/models/notification/email-templates-clinician.yaml` — Postmark template ID by clinic_id
  - `src/calendar/models/notification/email.service.ts` — Postmark integration（publish 到 `notification-email-template`）
  - `src/calendar/models/event/appointment-event.service.ts` (L88-99) — Kafka topic & broker 設定
  - `prisma/schema.prisma` — `v2_event` (L164+, status enum L237) / `v2_event_participant` / `v2_calendar` / `v2_reminder_audit_log` (新)
  - `src/calendar/models/accession-claim/` (新, VP-16410) — `AccessionClaimService` 提供 claim/release/sync/reset + audit；event.service 6 個 hook 點 (createEvent/createEventByPatient/updateEvent/updateEventByPatient/deleteEvent/deleteEventByPatient) 限 150105 自動 enforce 1:1 (`accession_id` UNIQUE)；GraphQL `resetEventAccession` (admin/clinicadmin/**clinicalteam**, PR #496) + `getClaimedAccessionIds` (clinic user)；docs 在 `docs/vp-16410-accession-claim.md`。
  - **Calendar RBAC 細節（`src/calendar/guard/auth.guard.ts`）**：`AuthGuard` 是 calendar 模組通用 guard；`validateClinicUser` 要求 clinic-user token 有 `user_id`+`clinic_id`，否則 `401 "Missing required clinic user identifiers"`（在進 resolver 前就擋）。`isAdminUser(user)` **只看 `user_roles[]`**（admin/clinic_admin/clinic）或 `user_permission`，**不看** `role`/`internal_user_role` 字串。`isClinicalTeamUser(user)` = `internal_user_role` 或 `role` === `'clinicalteam'`（內部跨 clinic、無 clinic_id，已在 guard 層豁免 identifier 檢查）。要放行某 role 做某 accession 操作 → guard(validateClinicUser 豁免) + resolver(allow-list) **兩處都要改**。
  - 詳細 email flow / Kafka 佈局見 `patterns.md` → "Clinical Consult Calendar Email Flow"
- **Base branch = `stage_test`**（非 staging/main）；feature PR → stage_test。
- **切 branch 後**（特別是不同 branch 的 `prisma/schema.prisma` 不同欄位／model 時）**必須跑 `npx prisma generate` + `npx prisma generate --schema=prisma2/schema2.prisma`** 對齊兩個 client（calendar / main LIS）。⚠️ **本 repo 的 `npm run build` 的 `prebuild` 只是 `rimraf dist`，不會 `prisma generate`**；`start:dev`/`build` 也都不會。客戶端 drift 會在 `npm run build` 跑出一堆 type error（如 18 個 `specialties` 錯）但實際 schema/code 沒問題。**絕對不要把這當「pre-existing / 假象」放掉** — 它意味著 client 對不上 schema，`npm run start:dev` 也會跟著炸（鐵律：start:dev 100% 要過）。VP-16521 session 翻車過：切 branch 沒 generate → 誤判為 stale 假象 → Leo 糾正。
- **Clinical Consult reschedule（VP-16520/16521, mutation `rescheduleClinicalConsult`, 150105-only）**：換 clinician = **cancel-and-rebook**（原 event `is_canceled=true` + 新 clinician 建新 event,F-8 抄 creator_calendar_id/practice_event_type/accession_ids,同 transaction release→claim accession 避 VP-16410 1:1 撞）;同 clinician = in-place update。`v2_event` **無 status enum,只有 `is_canceled` boolean** 驅動 open/pending reporting。email：switch=cancel(舊)+create(新)+update(provider)、same=update(clinician+provider),reuse 既有 Postmark template。side-effects（Kafka + 外部行事曆 sync + Zoom）比照 create/cancel/update,全 fire-and-forget。
- **Calendar DB schema 有三個**：`calendar_dev`（空 / 保留名）、`calendar_dev_new`（dev 主用）、`calendar_prod`。`.env` 內 `DATABASE_URL_CALENDAR` 用 `?schema=...` 指定。**Manual migration 一律先 `SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'calendar%'` enumerate 確認目標**，不要只 apply default schema
- **Calendar prod 連線**：`lis-postgresql.postgres.database.azure.com:5432 / ehr-admin` (PG)，user `ehradmin`，密碼在 `LIS-transformer-v2/.env` `DATABASE_URL_CALENDAR`（URL-encoded）。**Schema 用 `SET search_path = calendar_prod`**。Agent 端用 `/opt/homebrew/opt/libpq/bin/psql`（`brew install libpq`，keg-only 不會 symlink 到 PATH）。
- **`v2_event` Zoom URL 寫入規則（VP-16713 確立）**：
  - `external_url` (String?) — 完整 Zoom join URL（含 `?pwd=...`），patch 後 `zoom-event.service.ts:176-177` 從 `zoomService.createZoomMeeting().joinUrl` 寫入，**dashboard / reminder fallback 都讀這個**
  - `zoom_event_id` (String?) — Zoom meeting ID 純數字字串（從 `result.meetingDetails.meetingId`），**不是** URL；個人 PMI link（`/my/<vanity>`）沒有 ID
  - `location` (String? VARCHAR(500)) — 人類可讀文字（地址 / 備註），不是 URL 專用
  - **Reminder template fallback chain（`reminder.service.ts:237`）**：`location || zoom_event_id || external_url || ''`。Backfill `external_url` 時若 `location` 已有非空值，reminder 仍會優先顯示舊 location — 必要時須一併處理 location

### LIS-transformer
- **Purpose**: NestJS backend, REST (3190) + gRPC (3191)
- **Tech**: NestJS 10, TypeScript, Prisma
- **Key Areas**: `src/trans/` (patient data), `src/setting/` (clinic settings)
- **Note**: `src/trans/trans.service.ts` ~4000 lines

### lis-backend-emr-v2
- **Purpose**: EMR system backend (AutoIntegrate) — **future replacement for EMR-Backend (Java legacy)**
- **Tech**: NestJS, TypeScript, MySQL 8.0, Prisma, Kafka, BullMQ (sidecar Redis `emptyDir`)
- **Port**: 3000 (HTTP) / 5000 (gRPC self-server, prod NodePort `192.168.60.6:31317`)
- **⚠️ `.env DATABASE_URL` 指 prod**: `lisportalprod2.mysql.database.azure.com / lis_emr`，不是 dev。`prisma migrate deploy` / `db execute` / `db push` 前要先 verify schema element 存在。`_prisma_migrations` table **不存在於 prod**，所以 `prisma migrate status` 會報所有 migration 未 applied（schema 早已 manual SQL apply）— 別誤信 status，個別 `SHOW COLUMNS` / `SHOW TABLES` 驗證。
- **Repo convention `/scripts/` 在 `.gitignore`**：one-shot ts-node ops scripts（`_apply-*.ts`, `seed-*.ts`）不入版控。deploy-required 的 seed 改放 `prisma/seed.ts` 或 dump SQL fixture 進 migration folder；ad-hoc script 留 local。
- **JWT auth `isAdmin` derive 規則**：`auth.service.ts:36-41` 從 `internal_user_role` 比對 allowlist `['admin','super_admin','system_admin']` (lowercase) 算 isAdmin — payload 內直接寫 `isAdmin: true` 會被覆蓋。Bypass `validateCustomerAccess` / `validateApply` 要設 `internal_user_role: 'admin'`，不是 `'sales'`。Auth header 用 JWT_SECRET 從 .env 簽出來即可（HS256）。
- **授權是雙層,RBAC 改動要兩層都處理**（VP-16980）：(1) 全域 `APP_GUARD = JwtAuthGuard`（`app.module.ts`）—— 非 admin 且請求無 customer_id/clinic_id → `validateGeneralAccess` 要求 accessibleCustomer/ClinicIds 非空,否則 `403 "Access denied: no customer or clinic permissions"`；(2) controller 內 `validateCustomerAccess`/`validateClinicAccess`/`validateIntegrationAccess`（每個 controller 各自一份,散在幾乎每個 by-id 路由）。**只改 guard 不夠** → approve/reject 仍會被第二層擋。要放行某 role 存取整組 endpoint：用 `@SkipDataAccessCheck()` decorator（`auth/decorators/`,仿 `@Public`）—— guard 命中設 `user.skipDataAccess=true` 仍要求有效 JWT,各 access-helper 比照 `isAdmin` 加 `|| user.skipDataAccess` 提早 return。**區分兩種 gate**：customer/clinic ownership（可被 skipDataAccess 放行）vs `if(!user.isAdmin) throw 'Admin role required...'` 管理權限 mutation（**不該**被 skip 連帶放寬,保留）。「只給某內部角色」改判 `internal_user_role` 而非全開。
- **Branch / PR flow**：feature/leo/{ticket_id} → PR base=staging → 累積後另開 PR base=main ← head=staging rolling up。同一 feature branch 可有多個 PR (#116 / #118 / #120) 因為每次新 commit 起一張新 PR；最後 #121 把 staging 收進 main。「PR ready」不代表立刻進 main，要等 staging→main roll-up PR。
- **新 controller 掛 `@UseGuards(JwtAuthGuard)` → 該 controller 所屬 module 必須 import `AuthModule`**（`AuthModule` 非 @Global，export AuthService；JwtAuthGuard 注入 AuthService）。漏 import → 開機 `UnknownDependenciesException: JwtAuthGuard can't resolve AuthService` → **CrashLoopBackOff**。比照 ResultModule/SftpModule。`npm run build`(純 tsc) 與「手動 `new Service()` 單元測試」**都抓不到**這種 module-graph DI 錯，只有 app bootstrap 會炸（VP-16934 翻車：只跑 build 就部署，staging+prod 新 pod CrashLoop）。→ **鐵則 [[feedback_start_dev_iron_rule]]：prod-impacting deploy 前必跑 `npm run start:dev` 或 `Test.compile(AppModule)` 開機驗證**（範例 `scripts/_vp16934-boot-check.ts`）。
- **Key Areas**: `src/modules/ordering/`, `src/modules/result/`, `src/modules/hl7/`, `src/modules/integration-management/`, `src/modules/hl7-order-processing/`, `src/modules/queue/` (BullMQ), `src/modules/grpc/` (multi-tier upstream clients)
- **Scripts**: `scripts/insert-ehr-integration.ts`, `scripts/insert-order-client.ts`, etc.
- **Result generation entry**: `resultgeneration.ResultGenerationService/GenerateBatchResultsHl7` @ `192.168.60.6:31317` — proto `src/proto/result-generation.proto`，內部 fan-out 到 multiple distinct (legacy_emr_service, sftp_result_path) destinations，sequential
- **Generation pipeline structure**（INCIDENT-20260518 後）:
  - `prepareResultGenerationData` step 1-4 透過 `sample-test-result.service.ts` 的 `tryWithBackup` helper：v2 cloud primary / v1 on-prem fallback
  - Step 5 `getTestsResultsDetailData` 同樣 tryWithBackup pattern：cloud `10.224.0.199:30600` primary / on-prem lis-test-connect fallback
  - Step 6 reference range：v2 沒對應，只能 v1，加 30s deadline 讓 catch 繼續
  - 所有 await 都有 timeout（gRPC deadline / fetch AbortSignal / SFTP timeout）
  - BullMQ processor 包 `Promise.race` 10min hard timeout、concurrency=3
- **EMR-Backend → lis-backend-emr-v2 migration status (VP-15460)**:
  - **Stage 3a done**: SFTP fetch / HL7 parse / clinic resolution (via NPI lookup) in `src/modules/hl7-order-processing/processors/hl7-order.processor.ts`
  - **Stage 3b DONE (VP-16463, prod since ~2026-05-13)**: payment + sendOrder + emr_sample write ported to `src/modules/hl7-order-processing/services/order-finalizer.service.ts`. EMR-Backend `OrderTestClient` endpoints (BEST_DEAL / labProcessingFee / order / orderV2 / orderSetting / shortcut / paymentMethods / transactionPay) → wellness URLs in `EMR-Backend/.../orderApi.yaml` (most `api.vibrant-wellness.com`, except **BEST_DEAL on `api.vibrant-america.com`**). ~~Only VP-16463 batch-cutover clients route through emr-v2; others still hit Java EMR-Backend.~~ **UPDATE 2026-06-10 (Leo 確認)**: Java EMR-Backend 已**完全停用**——所有 EMR-originated order 現在都走 lis-backend-emr-v2（含 bestDeal / order / charging）。改 EMR order 行為只需動 emr-v2，不必動 EMR-Backend repo。
  - **LBS-1541 / bestDeal host**: emr-v2 `generateBestDeal()` (order-test-client.service.ts:35-41) 讀 `ORDER_BEST_DEAL_URL`，fallback hardcode `api.vibrant-america.com`。**cloud `api.` host 沒有 server-side 免費 Total Ig (id 167) add-on rule，只有 on-prem legacy `lis.vibrant-america.com` 有**（wellness 遷移時靜默掉的；orderApi.yaml「byte-identical 2026-05-11」註解是錯的）。interim fix = 在 config 設 `ORDER_BEST_DEAL_URL=https://lis.vibrant-america.com/...`，待 cloud bestDeal 更新後切回。同 token（VIBRANT_API_TOKEN）兩台 host 都收；改此 env 不牽連 charging/order（各自獨立 env）。
  - **⚠ 部署現況 (updated 2026-07-08, supersedes 2026-06-10「AKS 無 pod」)**: prod emr-v2 是**雙 pod 混合**——
    - **AKS pod** `lis-emr-v2-deployment-prod`（ns `emr-v2`，redis sidecar）：Phase A (VP-17291) 起 serve 所有 **endpoints**；Stage B (VP-17312, 2026-07-07) 起 `POD_ROLE=all` + `PIPELINE_LOCATION=cloud` + consumer group `emr-result-consumer-cloud-production`——pipeline 依 DB flag 分區，flags 全 onprem 時 idle。AKS egress IP `20.14.29.219`（外部 vendor SFTP allowlist 用）。
    - **on-prem pod**（appserver04）：`PIPELINE_LOCATION=onprem`，目前跑全部 pipeline（1263 integrations / 198 folders 全 onprem）。
    - **分區機制 (VP-17312)**：`pipeline_location ENUM('onprem','cloud')` 在 `ehr_integrations` / `sftp_folder_mapping` / `emr_periodic_report_customers` 三表，UPDATE 即時生效＝instant rollback。Stage C canary（ZymeBalanz→cloud→rollback）2026-07-08 全程 PASS。widening 前置：先修 VP-17342 silent-drop；同 (legacy_emr_service, sftp_result_path) dest 的 integrations 要一起 flip（VP-17343）；order 全留 on-prem（result-first）。
    - **Deploy 鏈**：main branch Jenkins build 一次做完 build image→on-prem rollout restart→ACR push→AKS apply（SHA-pin）——merge staging→main 的 release PR 即是部署。staging endpoints 也在 AKS（VP-17363, 2026-07-08，`/v1/lis/emr-service-staging`，web-only `-staging` 物件；staging DB 仍在 on-prem `192.168.60.11:3306`，AKS 可達已驗）。
    - `lis-emr-v2-config.yaml`(staging) 與 `lis-emr-v2-config-prod.yaml`(prod) 仍是 **gitignored 本地 ConfigMap 副本**；⚠ Jenkins 會把 AKS ConfigMap sync 到**兩邊** cluster——cloud-only env（如 KAFKA_CONSUMER_GROUP override）必須放 deployment 的 pod-level env（env 蓋 envFrom），不能進 ConfigMap。
    - ⚠ 既有 quirk：main build 會 restart default ns 的 on-prem **staging** pod 並把 image 重設回 `:latest`，蓋掉 staging branch 的 set image（VP-17363 驗證；staging cloud pod 不受影響）。
  - **Customer-pay charge flow**: `order-finalizer.service.ts` (charge branch: customerPay + stax method on file) → `ChargeClientService.getFirstPaymentMethod` + `transactionPay` → `api.vibrant-wellness.com/v1/charging/{paymentMethod/allSharedPaymentMethods, transaction/pay}`. Java ref = `ParseHL7.java:988-1006` + `ChargeClient.java`. Auth header has **no "Bearer " prefix** (Java quirk, intentionally preserved).
  - **⚠️ VP-16777 parity gotcha**: Java `TransactionPayInput` carries field-initializer defaults (`token_platform="stax"`, currency/charge_type/type/payment_source/new_sample). TS interfaces have **no runtime defaults** → caller must spread `TRANSACTION_PAY_DEFAULTS` (in `dto/payment.dto.ts`). Omitting `token_platform` makes the charging API silently not charge the card. See [[VP-16777]].
  - **emr-v2 不 durably 存 per-order 收費結果**: `order_intake_records` dormant（近期 0 筆）、`emr_sample` 不可靠當收費查詢源。查某 EMR order 收費/payment 狀態 → 上游 LIS-core / charging 系統。
  - **Result-side already ported**: `result-generation.service.ts` (getReportStatusListV2 + pdf-cache/download), `test-panel-mapping.service.ts` (packagePriceMapping + packageTestMapping), `scheduled-reports/base-report.service.ts` (csvReport via `VIBRANT_API_BASE_URL`), `ehr-email-notification.service.ts` (ehrEmailSupportForProvider/InnerTeam via `EHR_EMAIL_API_BASE_URL`)
- **Periodic report pipeline（客戶定期 SFTP 報告，`src/modules/scheduled-reports/`，VP-12605/VP-16987）**:
  - 觸發: NestJS `@Cron`（`quarterly/monthly/weekly-report.service.ts`，皆 extends `base-report.service.ts`）。quarterly `0 59 23 28-31 3,6,9,12 *` + `isLastDayOfQuarter()` guard（真正只在 3/31,6/30,9/30,12/31 跑）。`POD_ROLE` 未設=all→`isPusher` true 會跑；`ENVIRONMENT==='staging'` 會整段 skip。`@Cron` in-memory、無 catch-up（pod 在 fire 當下沒活就 miss）。cron-status 端點 `/api/v1/scheduled-reports/cron-status`（需 JwtAuthGuard）。
  - 收件人 table: `emr_periodic_report_customers`（customer_id/clinic_id/host/port/username/password/folder_path/frequency；**無 enabled 欄**，有 row 就發）。交付紀錄 table: `periodic_report_records`，unique=(customer_id, accession_id, report_period)→**每 accession 一筆**。
  - 資料流: gRPC `getCustomerSamplesByTimeRange` → ClickHouse `general_event_data`(report_finished/redraw_report_finished) → 逐 accession 打 `VIBRANT_API_BASE_URL/result/csvReport?barcode=` 取 CSV → 組 XLSX(每 accession 一 sheet) → SFTP 上傳 → 寫 record。產出是 **.xlsx**（非 .csv）。
  - **csvReport CSV 欄位（14 欄, 0-indexed）**: 0 SampleId,1 BarcodeTubeId,2 TestId,3 TestName,4 PatientId,5 PatientName,6 TestResult,7 ResultUnit,8 ResultRangeType,9 NormalRangeMin,10 NormalRangeMax,11 ReportableRangeMin,12 ReportableRangeMax,**13 ReportGeneratedTimeStamp**。資料列尾有逗號(naive split→15 欄)、CRLF。`ReportGeneratedTimeStamp` 是 on-demand API 產生當下時間(≈now)，非歷史報告時間。
  - **VP-16987 坑**: 舊 code 讀 `column[12]`(ReportableRangeMax 數字)當 timestamp→`new Date("170")`=年0170<MySQL DATETIME 下限→`createMany` 對全部 customer throw、被 per-customer catch 靜默吞→`periodic_report_records` 全空、客戶斷交付。修法(PR #175): quote-aware parse + 用 header 名定位欄 + 日期範圍驗證 + record 寫入獨立於 SFTP try（bookkeeping 失敗不可 mask 成功交付）。**debug 此類隱形失敗：先把 catch 改印 stack / 觸發真實路徑復現，別信 error.message（Prisma error message 為空）。**

### LIS-backend-v2-coreSamples
- **Purpose**: Core lab samples, orders, customers
- **Tech**: Go 1.19+, go-micro v4, Ent ORM, MySQL, Redis, Kafka
- **Ports**: gRPC 8084, HTTP 8083
- **Setup**: `make proto && make ent && ./dev.sh`

### EMR-Backend
- **Purpose**: Legacy Java EMR order parsing (being migrated to emr-v2)
- **Tech**: Java 8, Maven, MyBatis, gRPC
- **Build**: Run mybatis-generator + protobuf plugins, then `mvn package`

### LIS-backend-results-grpc
- **Purpose**: gRPC server for test results — `testresult.TestResultInfoGrpcService` (`getTestsResultsDetailData` 等). lis-backend-emr-v2 result generation step 5 的下游
- **Image**: `lisportalprod.azurecr.io/vibrant/lis-test-connect:latest` (container name "lis-test-connect-deployment" in K8s; service name in log: `LIS-RESULTS-GRPC`)
- **Endpoints**:
  - on-prem prod: `192.168.60.6:30600` (NodePort → svc `lis-test-connect-grpc-service` → 2 replicas)
  - cloud: `10.224.0.199:30600` (same proto/service, currently healthy — emr-v2 用作 primary)
- **Key file**: `src/features/grpc/grpc.controller.ts` (`getTestsResultsDetailData` handler entry)
- **Server log entry signature**: `service: "tests results with sampleId or barcode with detail parse"` 印一行後若無下文 → handler hang 在 Redis lookup（INCIDENT-20260518 root cause）
- **Known weakness**: handler 內走 Azure Redis `vibrant-cloud-cache.redis.cache.windows.net` 的 cache lookup 無 timeout；當 Redis NXDOMAIN 時 handler 永遠不返回。Readiness probe 是 `/swagger` HTTP，不檢查 Redis，所以 K8s 仍認為 pod 健康繼續吃流量

### LIS-backend-results-core
- **Purpose**: Zixi 的 results service — Kafka events → MySQL + Redis pending list + approval workflow
- **Tech**: NestJS hybrid, TypeScript, MySQL, Redis, 11 Kafka consumer groups → 19 Bull queues, gRPC clients to Info/Result/Issue/AuditLog/User/Comment
- **Ports**: HTTP 3000 + gRPC 6789
- **Pending list 雙層 Redis Set**（PO-222 學到）:
  - `pending_tests` (master Set of tag strings)
  - `pending::{barcode}::{instrument}::{sampleType}::{recvDate}::{sampleId}::{collDate}::{testName}::{instrument}` (tag Set，member 是 testId)
  - `lis::full::pending_tests` (frontend JSON cache, ~60s regenerate, portal 直讀；不清這個 UI 不會更新)
- **Approval pending list（不同 Set，別搞混）**: `lis::approve::pending*` + `lis_approve_pending_list` — 由 `/grpc-result/fix-missing-approval-pending` admin endpoint 重建（race-prone：先讀 DB snapshot、後 SADD Redis）
- **手動清 ghost pending 腳本**: `scripts/remove-from-pending-complete.js <barcode> <testName>` — 同時清 backend `pending_tests` Set + frontend `lis::full::pending_tests` JSON cache
- **getEnvKey 陷阱**: `src/redisKeyList.ts:8` 只對含 `lis::pending` 字串的 baseKey 加 env suffix；`getEnvKey('pending_tests')`、`getEnvKey('approve_pending_tests')` 等實際在所有環境都是同名（靠不同 Redis 主機隔離環境）
- **Approve race condition (PO-222 root cause)**: `test-approve.service.ts:199-216` 順序是先 SREM Redis → 後 UPDATE DB；同時 flush endpoint 是先 SELECT DB → 後 SADD Redis。兩者並發必有 race window
- **Pre-commit hook 壞掉**：CRLF 問題，commit 用 `--no-verify`

### LIS-setting-consumer
- **Purpose**: Kafka consumer for notifications (email, SMS, push)
- **Tech**: NestJS 9.3, Bull/Redis queues, 20+ Kafka topics
- **Port**: 6457
- **Note**: `setting-consumer.controller.ts` ~16K lines

### On-prem K8s 存取（appserver04 + 192.168.60.5）
EMR-Backend (Java v1, deployment `lis-emr-prod`) + lis-backend-emr-v2 (NestJS, deployment `lis-emr-v2-deployment` + `lis-emr-v2-deployment-prod`) 都 pinned 在 on-prem node `appserver04` (= IP `192.168.60.5`)。本機 kubeconfig `lisportalprod` 連的是 **Azure AKS**，看不到 on-prem 的 pod、SSH 進 appserver04 才能 `kubectl`。

**SSH**: `ssh leo@192.168.60.5`（密碼問 Leo；本 session 用過、有效）。SSH 上去後直接 `kubectl get pods` / `kubectl logs <pod> -c <container>` / `kubectl rollout restart deployment <name>`。

**On-prem 用 expect 跑 kubectl（從 Mac 自動化）**:
```bash
expect << 'EOF'
set timeout 30
spawn ssh -o StrictHostKeyChecking=no leo@192.168.60.5
expect "password:"; send "<pw>\r"
expect -re {\$ ?$}
send "kubectl logs <pod> -c <container> --since=10m\r"
expect -re {\$ ?$}; send "exit\r"; expect eof
EOF
```
sudo prompt 用 `echo <pw> | sudo -S <cmd>`。Heredoc 內含 `[^...]` 之類 expect 會誤判 → 改寫 script base64 編碼再 `base64 -d | bash`。

**Pod naming（容易混）**:
- `lis-emr-prod-<hash>-<id>` = **V1 Java** EMR-Backend (image `192.168.60.10:6004/prod/emr/execute_all:latest`)
- `lis-emr-v2-deployment-prod-<hash>-<id>` = **V2 NestJS** prod
- `lis-emr-v2-deployment-<hash>-<id>` = **V2 NestJS** staging（同 cluster 同 node、不同 deployment，連 staging DB `192.168.60.11`）
- AKS ns `emr-v2` 另有 `lis-emr-v2-deployment-prod-*`（prod cloud pod，VP-17291/17312）與 `lis-emr-v2-deployment-staging-*`（staging endpoints 上雲，VP-17363）——與 on-prem deployment 名字相近但分屬不同 cluster，看 kubectl context 別搞混

**Node-level container log path**（pod 已 GC 後）: `/var/log/pods/default_<podname>_<uid>/<container>/0.log` symlink 到 `/var/lib/docker/containers/<id>/<id>-json.log`。需要 sudo。**但 GC 後 docker container json log 也會清**、別賴它做 post-mortem。

**Pod restart 前必先 preserve evidence** — 見 [[INCIDENT-20260528]] failure：destructive ops (rollout restart / pod delete) 前一定要 `kubectl logs <pod> > /tmp/X.log` + `kubectl describe pod <pod> > /tmp/X_desc.txt` 存證，否則 root cause 隨 pod GC 永久遺失。

## Inactive/Empty
- EHR-backend, LIS-backend-billing, LIS-backend-coreSamples, LIS-backend-v2-order-management — empty or minimal
