---
id: repos
type: ltm
category: technical
status: active
score: 0.1448
base_weight: 0.9
created: 2026-04-22
updated: 2026-10-26
links:
- INCIDENT-20260518
- INCIDENT-20260528
- INCIDENT-20260601-sftp-hang
- INCIDENT-20260604
- INCIDENT-20260817-onprem-deploy-freeze
- INCIDENT-20260908-grpc-dead-node-ip
- INCIDENT-20260910-emr-v2-di-crashloop
- LBS-1487
- LBS-1547
- LIS-7882
- PO-222
- PO-270
- PO-273
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
- TRANS-OPTIMIZATION-20260911
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
- VP-17412
- VP-17421
- VP-17422
- VP-17559
- VP-17561
- VP-17577
- VP-17714
- VP-17753
- VP-17754
- VP-17755
- VP-17765
- VP-17766
- VP-17825
- VP-17868
- VP-17870
- VP-18048
- VP-18050
- VP-18303
- VP-18320
- VP-18342
- VP-18344
- VP-18347
- VP-18400
- VP-18406
- VP-18460
- VP-18461
- VP-18462
- VP-18463
- VP-18464
- VP-18466
- VP-18474
- VP-18480
- VP-18481
- VP-18482
- VP-18485
- VP-18655
- VP-18673
- VP-18749
- VP-18770
- VP-18771
- VP-18782
- VP-18796
- VP-18801
- VP-18802
- VP-9299
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
- **TRANS-OPT（2026-09-14/15）**：Datadog service `lis-transv2-deployment`；deploy = GitHub Actions `frontend-service-graphql`（main）/ `-st`（stage_test）；configMap `transv2/lis-transv2-config`。S2 直連 gRPC 在 `TRANS_PROXY_GRPC_MODE`（http/shadow/grpc，prod 目前 shadow）；
  `checkIfPersonalizedReportCanBeCreated` 已從 cloud-local-proxy 改直打 on-prem 192.168.60.77:8081（S1，config only）。PatientProfileSlow 的 p95 尾巴在 shipping `horm-qnr/status` 與 interactive-report，不在本 repo。v2 `shipping.proto` 已補齊 v1 的 GetKitStatusBySampleId / GetQuestionaireBySampleId。計畫與量測：working-agent repo `docs/plans/trans-optimization/`。
- **Purpose**: LIS frontend GraphQL API gateway
- **Tech**: NestJS 11, TypeScript, Prisma (PostgreSQL + MySQL dual schema)
- **Port**: 3390。**部署端點（LIS-7690 實測 2026-08-18，詳見 repo README PR #571）**：AKS-only（ns `transv2`，無 on-prem、無 NodePort）——prod `https://api.vibrant-america.com/v2/portal/trans-service` → svc `lis-transv2-service:3246`（3 replicas）、staging `.../trans-service-st` → `:3247`。GraphQL introspection 兩個 cloud env 都**關**（僅 `platform_type==='local'` 開，Bishop Fox hardening，不是故障）。**v1/v2 前綴分界**：`/v1/...`（含 wellness `/v1/portal/trans-service`、`/v1/portal/calendar`）全部是 v1 `LIS-transformer`；本 repo 只服務 `/v2/portal/trans-service`。Service/Ingress 物件不在 repo yaml，只在 cluster。
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
  - **accession 1:1 guard 的設計缺口 = `resetEventAccession`（VP-17577 P1「重複預約」的真因，2026-07-31 Leo 裁定 works-as-designed）**：guard 只保證「一個 accession 同時只被一筆 claim 佔用」，**不檢查被 reset 掉的那筆 event 是否還活著**。所以 `clinicalteam` 對一個 accession 按 reset 之後，原本那場未來的 consult **仍然是 live event**，accession 又能被重新 claim → 同一 accession 出現**兩場 live 未來 consult**，而 VP-16410 的 UNIQUE 從頭到尾沒被違反（查 claim 表看不出問題，要查 event）。
    - 規模（2026-07-31 量測）：5 月以來 **245 次 reset-while-active**，其中 **23 次 reset 的是未來的 event**；當下有 **2 個 accession 各持有 2 場 live 未來 consult**。所以這不是單一事故，是常態操作。
    - 診斷起點：拿 accession audit 的 actor（`user:N` = `lis_core_v7.user_id`，解析路徑見 memory「Calendar audit actor id lookup」）比對 reset 時間 vs. event 的 `is_canceled`/開始時間 —— **reset 時間落在一場 live 未來 event 之後 11 分鐘**就是這個形狀。
    - 想真的堵掉要在 reset 路徑加「原 event 尚未 cancel 就拒絕／連帶 cancel」，屬產品決策；Leo 目前選擇不改 code。
  - **Batched claim status `claimStatuses`（VP-18050，PR #592→main / #593→stage_test，2026-08-31 皆 draft 未 merge）**：一次查多個 accession 的 claim 狀態＋consult date，服務 VP-18051 的搜尋結果 row-level「Consult booked」標籤（該 FE 未做，Leo 裁定）。設計約束是 disclosure gate 不是效能：`isAccessionClaimable` 收任意 accession id、不驗屬於 caller 的 clinic（VP-17868 因此把 `consultDate` 鎖在「viewer 綁在該 consult」後），batch 端點放大暴露面 → gate **逐 row 套用**、batch cap 20（理由寫進常數 doc comment，防止被當 throughput 旋鈕調大）、`isClaimable`/`claimStatuses` 共用同一 select + row-to-answer mapping（隱私控制不能有兩份會靜默分歧的複本）。
    - **Row-level claim 資料進不了搜尋 response**：`SearchOrders.vue` 的 `loginServiceCloud.post('/trans/findPatient')` 由 **v1 LIS-transformer** 服務（無 calendar_prod 存取，且同時支撐 patient page），不是 transv2——別想把欄位塞進 findPatient。`getClaimedAccessionIds` 也不合用（回 150105 全部 ~3,640 claimed id、不帶日期、va-portal/wellness-portal 零 consumer）。
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
- **TRANS-OPT（2026-09-14/15）**：Datadog service `lis-trans-deployment`；deploy = GitHub Actions `lis-transformer-deploy-prod`（main）/ `-staging`（stage_test）；configMap `default/lis-trans-config`。已上 prod：findPatient 並行化（#769）、createPatient 共用 Kafka producer（#773）、getTimeLine 排程（#774）+ kit status in-process（#776，`TRANS_TIMELINE_KIT_MODE` http/shadow/inprocess，prod shadow）、newrange prefetch（#775）。
  `getPatient.service.ts:410-418` 的跨請求 instance 欄位污染、`src/redis_s.ts` hard-code Redis 憑證等 pre-existing 缺陷列在 VP-18276。prod 仍有 14 個 `cloud-proxy` config key 沒有 reader（可清）。
- **Purpose**: NestJS backend, REST (3190) + gRPC (3191)
- **Tech**: NestJS 10, TypeScript, Prisma
- **Key Areas**: `src/trans/` (patient data), `src/setting/` (clinic settings), `src/calendar/email/`（legacy consult-reminder Bull processor，Portal-Calendar 遷入）
- **Note**: `src/trans/trans.service.ts` ~4000 lines
- **⚠ Reminder Bull queues（VP-17421）**: `reminder_24h/48h/15m` 在 **on-prem redis `192.168.60.9:4646`**（`calendarRedisOptions`: stprod/mac→on-prem，其他→Azure），由 `lis-trans-deployment-st`（SERVER_ENVIRONMENT=stprod）pod 消費並寄**真 prod email**（VP-16921 同款 smell，已 flag 給 Leo）。processor 的 future-date guard = PR #562。排查指紋見 patterns.md「Consult reminder 兩個 producer 並存」。

### lis-backend-emr-v2
- **Purpose**: EMR system backend (AutoIntegrate) — **future replacement for EMR-Backend (Java legacy)**
- **Tech**: NestJS, TypeScript, MySQL 8.0, Prisma, Kafka, BullMQ (sidecar Redis `emptyDir`)
- **Port**: 3000 (HTTP) / 5000 (gRPC self-server)。on-prem NodePorts：prod gRPC `192.168.60.6:31317`、prod HTTP `31318`（31316 是死的 legacy port，yaml 註解已改、Jenkinsfile echo 仍殘留）；staging gRPC `31319` / HTTP `31320`。**另有兩個 repos 先前漏記的 live gRPC NodePorts（LIS-7690 cluster 實測 2026-08-18）**：`28305`（`lis-emr-v2-grpc-service-prod`）、`28301`（`lis-emr-v2-grpc-service`），都 → container 5000；in-cluster 另有 `lis-emr-v2-internal-{prod,staging}` 與舊 ClusterIP `lis-emr-v2-http-service{,-prod}`（28300/28302→3000）。公開 HTTPS 端點全表在 **emr-v2 README「Service Endpoints」section（PR #377）**，全部 live 驗證過。⚠ on-prem prod image tag 是 **`:latest` 非 SHA-pinned** — INCIDENT-20260817 十三天 silent drift 的結構性成因，未修。
- **PR / deploy 慣例（2026-09-09 實測）**：feature → `staging` PR → `staging → main` release PR（標題 "Staging"）；沒有 `stage_test` branch。部署是 Jenkins（commit status），GH Actions 只跑 CodeQL。健康路徑 `GET /api/v1/health`。詳 patterns.md 【蒸餾 2026-09-11】。
- **⚠️ `.env DATABASE_URL` 指 prod**: `lisportalprod2.mysql.database.azure.com / lis_emr`，不是 dev。`prisma migrate deploy` / `db execute` / `db push` 前要先 verify schema element 存在。`_prisma_migrations` table **不存在於 prod**，所以 `prisma migrate status` 會報所有 migration 未 applied（schema 早已 manual SQL apply）— 別誤信 status，個別 `SHOW COLUMNS` / `SHOW TABLES` 驗證。
- **Repo convention `/scripts/` 在 `.gitignore`**：one-shot ts-node ops scripts（`_apply-*.ts`, `seed-*.ts`）不入版控。deploy-required 的 seed 改放 `prisma/seed.ts` 或 dump SQL fixture 進 migration folder；ad-hoc script 留 local。
- **JWT auth `isAdmin` derive 規則**：`auth.service.ts:36-41` 從 `internal_user_role` 比對 allowlist `['admin','super_admin','system_admin']` (lowercase) 算 isAdmin — payload 內直接寫 `isAdmin: true` 會被覆蓋。Bypass `validateCustomerAccess` / `validateApply` 要設 `internal_user_role: 'admin'`，不是 `'sales'`。Auth header 用 JWT_SECRET 從 .env 簽出來即可（HS256）。
- **授權是雙層,RBAC 改動要兩層都處理**（VP-16980）：(1) 全域 `APP_GUARD = JwtAuthGuard`（`app.module.ts`）—— 非 admin 且請求無 customer_id/clinic_id → `validateGeneralAccess` 要求 accessibleCustomer/ClinicIds 非空,否則 `403 "Access denied: no customer or clinic permissions"`；(2) controller 內 `validateCustomerAccess`/`validateClinicAccess`/`validateIntegrationAccess`（每個 controller 各自一份,散在幾乎每個 by-id 路由）。**只改 guard 不夠** → approve/reject 仍會被第二層擋。要放行某 role 存取整組 endpoint：用 `@SkipDataAccessCheck()` decorator（`auth/decorators/`,仿 `@Public`）—— guard 命中設 `user.skipDataAccess=true` 仍要求有效 JWT,各 access-helper 比照 `isAdmin` 加 `|| user.skipDataAccess` 提早 return。**區分兩種 gate**：customer/clinic ownership（可被 skipDataAccess 放行）vs `if(!user.isAdmin) throw 'Admin role required...'` 管理權限 mutation（**不該**被 skip 連帶放寬,保留）。「只給某內部角色」改判 `internal_user_role` 而非全開。
- **Branch / PR flow**：feature/leo/{ticket_id} → PR base=staging → 累積後另開 PR base=main ← head=staging rolling up。同一 feature branch 可有多個 PR (#116 / #118 / #120) 因為每次新 commit 起一張新 PR；最後 #121 把 staging 收進 main。「PR ready」不代表立刻進 main，要等 staging→main roll-up PR。
- **新 controller 掛 `@UseGuards(JwtAuthGuard)` → 該 controller 所屬 module 必須 import `AuthModule`**（`AuthModule` 非 @Global，export AuthService；JwtAuthGuard 注入 AuthService）。漏 import → 開機 `UnknownDependenciesException: JwtAuthGuard can't resolve AuthService` → **CrashLoopBackOff**。比照 ResultModule/SftpModule。`npm run build`(純 tsc) 與「手動 `new Service()` 單元測試」**都抓不到**這種 module-graph DI 錯，只有 app bootstrap 會炸（VP-16934 翻車：只跑 build 就部署，staging+prod 新 pod CrashLoop）。→ **鐵則 [[feedback_start_dev_iron_rule]]：prod-impacting deploy 前必跑 `npm run start:dev` 或 `Test.compile(AppModule)` 開機驗證**（範例 `scripts/_vp16934-boot-check.ts`）。
- **Spec/jest gotchas**：(1) `result.service` 以 bracket notation 取用 generation service 的 private 成員（`this.resultGenerationService['grpcClientService']`）→ spec mock 必須提供該 nested shape（VP-17343）。(2) repo 內有 `.claude/worktrees/` 分支副本，`npx jest <path>` 會把 worktree 內同名檔一起跑 → 一律加 `--testPathIgnorePatterns=worktrees`（VP-17344）。(3) ~~full jest 在 clean origin/staging 本來就有 ~25 個壞 suite~~ **RESOLVED 2026-07-13/14（VP-17407 PR #256 + VP-17408 PR #258）**：`npm test` 現在 clean checkout 82/82 suites 綠、parallel==serial。當年兩個根因：`test/setup.ts` 的 per-file `afterAll` 跑 `cleanupAllTestDatabases()`（`rm -rf test-*.db`）砍掉其他 worker 的活 DB（"table does not exist" 只在 parallel 出現）＋ per-suite `prisma db push` 沒 `--skip-generate` 會 mid-run 重生 shared test-client；另外 24 個 suite 是 stale spec（對舊 API 寫的），已全部現代化。**回歸判定不再需要 stashed baseline — 紅了就是你弄的。**(4) jest 的 FAIL 行會印兩次（run + summary），數失敗 suite 前先 dedupe。(5) `prisma/test.db` 是被 track 的 binary、測試會重建它 — diff 髒了屬預期。(6) pre-commit config-yaml-coupling hook 對任何靠近 `ORDER_INTAKE_MODE` 用法或 downward-API env（`MY_POD_NAME` fieldRef）的 commit 會 false positive（它要的兩個 yaml 不在 repo）— `--no-verify` 加說明，CJK check 手動跑（#249-#266 慣例）。
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
    - **on-prem pod**（appserver04）：`PIPELINE_LOCATION=onprem`，跑 order pipeline 全部（198 folders 全 onprem）＋大多數 result integrations（2026-07-09 起 result 開始分批 flip 到 cloud，見下）。
    - **分區機制 (VP-17312)**：`pipeline_location ENUM('onprem','cloud')` 在 `ehr_integrations` / `sftp_folder_mapping` / `emr_periodic_report_customers` 三表，UPDATE 即時生效＝instant rollback。Stage C canary（ZymeBalanz→cloud→rollback）2026-07-08 全程 PASS。
    - **Result widening 進度（2026-07-09）**：batch-1 (THM/GLO/HealthMatters ×22) + batch-2 (ECW/VEJO×3系/Unprescribed/YHL ×30) 共 **52 integrations 已在 cloud**（全部 .155 Vibrant 內部 SFTP）；batch-3 = OPTIMANTRA ×46，Leo 已預先授權，monitor 於首筆 organic cloud delivery peer-verify 後自動執行；PRAXISEMR ×3 因 whole-customer 綁 MDHQ 順延至 batch-4 (MDHQ ~400，需 VP-17343 已 deploy ✓)；batch-5 = 外部 vendor（需 AKS egress `20.14.29.219` allowlist outreach，未指派）。前置 VP-17342 silent-drop fix 已上 prod（image d7c938e）。
    - **Flip 規則**：whole-destination（同 (legacy_emr_service, sftp_result_path) 的 integrations 一起 flip）+ whole-customer（同 customer 的所有 LIVE result integrations 一起）；repush 留 on-prem gRPC；VP-17343 已補 TIMEOUT_RETRY per-integration fan-out + 跨 location 生成 WARN。⚠ whole-customer 衝突檢查：customer-level rows join customer_id，**clinic-level rows（customer_id='-1'）要 join clinic_id** —— 拿 '-1'='-1' join 會誤報大量衝突。
    - **Order-side cutover**：code/DDL 已隨 VP-17312 出貨（fetch cron filter + requeue ownership + `sftp_folder_mapping.pipeline_location`，198 rows 全 onprem）、尚未 flip。Runbook = working-agent repo `runbooks/vp17312-order-cutover.md`（flip 單位=folder、flip 前 DRAIN retriable rows、tick 之間執行）。Cloud pod 對 8 個 inbound host 可達性 7/8 OK；**Breathermae 64.124.9.100:2222 從 cloud timeout 且 30d 零流量 → 留 onprem/考慮退役**。Folder→host 解析走 `emrName→emr_sftp_source`（不是 sftp_source_id）；VP-17385 正在把 order-fetch 憑證改為 `ehr_vendors` primary + legacy fallback。
    - **Deploy 鏈**：main branch Jenkins build 一次做完 build image→on-prem rollout restart→ACR push→AKS apply（SHA-pin）——merge staging→main 的 release PR 即是部署。staging endpoints 也在 AKS（VP-17363, 2026-07-08，`/v1/lis/emr-service-staging`，web-only `-staging` 物件；staging DB 仍在 on-prem `192.168.60.11:3306`，AKS 可達已驗）。staging deploy 延遲實測：merge → AKS staging pod 跑新 image 約 **25 分鐘**（VP-17342, 2026-07-09）。
    - `lis-emr-v2-config.yaml`(staging) 與 `lis-emr-v2-config-prod.yaml`(prod) 仍是 **gitignored 本地 ConfigMap 副本**；⚠ Jenkins 會把 AKS ConfigMap sync 到**兩邊** cluster——cloud-only env（如 KAFKA_CONSUMER_GROUP override）必須放 deployment 的 pod-level env（env 蓋 envFrom），不能進 ConfigMap。
    - ⚠ 既有 quirk：main build 會 restart default ns 的 on-prem **staging** pod 並把 image 重設回 `:latest`，蓋掉 staging branch 的 set image（VP-17363 驗證；staging cloud pod 不受影響）。
  - **Customer-pay charge flow**: `order-finalizer.service.ts` (charge branch: customerPay + stax method on file) → `ChargeClientService.getFirstPaymentMethod` + `transactionPay` → `api.vibrant-wellness.com/v1/charging/{paymentMethod/allSharedPaymentMethods, transaction/pay}`. Java ref = `ParseHL7.java:988-1006` + `ChargeClient.java`. Auth header has **no "Bearer " prefix** (Java quirk, intentionally preserved).
  - **⚠️ VP-16777 parity gotcha**: Java `TransactionPayInput` carries field-initializer defaults (`token_platform="stax"`, currency/charge_type/type/payment_source/new_sample). TS interfaces have **no runtime defaults** → caller must spread `TRANSACTION_PAY_DEFAULTS` (in `dto/payment.dto.ts`). Omitting `token_platform` makes the charging API silently not charge the card. See [[VP-16777]].
  - **⚠️ UPDATE 2026-07-13/14（部分推翻上條，PR #255/#264/#263, VP-17286/VP-17411）**：charging **不會**從 token 反解 platform — `type`/`token_platform` 必須**跟著選中的 payment method 走**，stax defaults 只當 fallback（Java parity 硬編 stax 對 stripe method 是錯的）。stripe card 走 stax 憑證會 400（`Credit Card Error:` 空 stax_error = mismatch 特徵）；stripe card 走 stripe 會 2xx `requires_confirmation` + **空 payment_id（錢沒動）**，unattended flow 無法 confirm；stripe ACH charging 端 call Stripe 格式壞掉（404 空 id）。**#264 guard：finalizer success 必須有 `payment_transaction_id`**，否則記 fail reason（HL7 照 Java 語意出貨但可見；API path 直接擋）。**API path 正式規則（Leo 2026-07-14，#263 test-locked）**：customerPay 必須付款成功否則 error（不同於 HL7/EMR path 的「出貨＋記 fail reason」）；patientPayLater 無卡正常下單。文件：`docs/ORDER-PIPELINE.md`。prod 大宗是 stax-first，不受影響；stripe-first 客戶要真正可收費還缺 charging 端 off-session auto-confirm（VP-17411 追）。
  - **emr-v2 不 durably 存 per-order 收費結果**: `order_intake_records` dormant（近期 0 筆）、`emr_sample` 不可靠當收費查詢源。查某 EMR order 收費/payment 狀態 → 上游 LIS-core / charging 系統。
  - **Result-side already ported**: `result-generation.service.ts` (getReportStatusListV2 + pdf-cache/download), `test-panel-mapping.service.ts` (packagePriceMapping + packageTestMapping), `scheduled-reports/base-report.service.ts` (csvReport via `VIBRANT_API_BASE_URL`), `ehr-email-notification.service.ts` (ehrEmailSupportForProvider/InnerTeam via `EHR_EMAIL_API_BASE_URL`)
- **Periodic report pipeline（客戶定期 SFTP 報告，`src/modules/scheduled-reports/`，VP-12605/VP-16987）**:
  - 觸發: NestJS `@Cron`（`quarterly/monthly/weekly-report.service.ts`，皆 extends `base-report.service.ts`）。quarterly `0 59 23 28-31 3,6,9,12 *` + `isLastDayOfQuarter()` guard（真正只在 3/31,6/30,9/30,12/31 跑）。`POD_ROLE` 未設=all→`isPusher` true 會跑；`ENVIRONMENT==='staging'` 會整段 skip。`@Cron` in-memory、無 catch-up（pod 在 fire 當下沒活就 miss）。cron-status 端點 `/api/v1/scheduled-reports/cron-status`（需 JwtAuthGuard）。
  - 收件人 table: `emr_periodic_report_customers`（customer_id/clinic_id/host/port/username/password/folder_path/frequency；**無 enabled 欄**，有 row 就發）。交付紀錄 table: `periodic_report_records`，unique=(customer_id, accession_id, report_period)→**每 accession 一筆**。
  - 資料流: gRPC `getCustomerSamplesByTimeRange` → ClickHouse `general_event_data`(report_finished/redraw_report_finished) → 逐 accession 打 `VIBRANT_API_BASE_URL/result/csvReport?barcode=` 取 CSV → 組 XLSX(每 accession 一 sheet) → SFTP 上傳 → 寫 record。產出是 **.xlsx**（非 .csv）。
  - **csvReport CSV 欄位（14 欄, 0-indexed）**: 0 SampleId,1 BarcodeTubeId,2 TestId,3 TestName,4 PatientId,5 PatientName,6 TestResult,7 ResultUnit,8 ResultRangeType,9 NormalRangeMin,10 NormalRangeMax,11 ReportableRangeMin,12 ReportableRangeMax,**13 ReportGeneratedTimeStamp**。資料列尾有逗號(naive split→15 欄)、CRLF。`ReportGeneratedTimeStamp` 是 on-demand API 產生當下時間(≈now)，非歷史報告時間。
  - **VP-16987 坑**: 舊 code 讀 `column[12]`(ReportableRangeMax 數字)當 timestamp→`new Date("170")`=年0170<MySQL DATETIME 下限→`createMany` 對全部 customer throw、被 per-customer catch 靜默吞→`periodic_report_records` 全空、客戶斷交付。修法(PR #175): quote-aware parse + 用 header 名定位欄 + 日期範圍驗證 + record 寫入獨立於 SFTP try（bookkeeping 失敗不可 mask 成功交付）。**debug 此類隱形失敗：先把 catch 改印 stack / 觸發真實路徑復現，別信 error.message（Prisma error message 為空）。**

### LIS-backend-v2-coreSamples
  - **這條 flow 的 JWT 用 Leo 的 admin 身分，且只限這條 flow**（2026-08-16 遷入自 auto-memory；code 現況已如此）：`base-report.service.ts` 的 `generateJwtToken()` 簽的 payload 是 `userId/user_id 142346`、`internal_user_id 1201`、`internal_user_name "hung.l"`、`role/internal_user_role "admin"`，其餘 customer/clinic/patient 欄位皆 null，取代原本寫死的假 user 54674 / role `"ss"`。理由：這是 server 主動跑的 scheduled job，不是 end-user 觸發的。**不要把這組 payload 套到其他下載 report 的場景**——end-user 透過 API 下載自己的 report 時應該用 caller 自己的 JWT。`iat`/`exp` 交給 `JwtService.sign()` 依 `expiresIn` 產生，不要寫死；仍用 env `JWT_SECRET` 簽發。
- **Purpose**: Core lab samples, orders, customers
- **Tech**: Go 1.19+, go-micro v4, Ent ORM, MySQL, Redis, Kafka
- **Ports**: gRPC 8084, HTTP 8083
- **Setup**: `make proto && make ent && ./dev.sh`

### EMR-Backend
- **Purpose**: Legacy Java EMR order parsing (being migrated to emr-v2)
- **Tech**: Java 8, Maven, MyBatis, gRPC
- **Build**: Run mybatis-generator + protobuf plugins, then `mvn package`
- **部署狀態（LIS-7690 cluster 實測 2026-08-18）**：on-prem 四個 deployment（`lis-emr-prod`/`lis-emr-result-prod`/`lis-emr-dev`/`lis-emr-result-dev`）**全部 0/0 replicas = 完全停止**；`emr-prod` Service（50051→NodePort 31316）還在但無人應答，`~/src` 下無任何 repo 引用該 port。VP-17460 的「兩條 Java reader path 待確認」在 deployment 層面已不可能在跑。

### LIS-backend-results-grpc
- **Purpose**: gRPC server for test results — `testresult.TestResultInfoGrpcService` (`getTestsResultsDetailData` 等). lis-backend-emr-v2 result generation step 5 的下游
- **Image**: `lisportalprod.azurecr.io/vibrant/lis-test-connect:latest` (container name "lis-test-connect-deployment" in K8s; service name in log: `LIS-RESULTS-GRPC`)
- **Endpoints**:
  - on-prem prod: `192.168.60.6:30600` (NodePort → svc `lis-test-connect-grpc-service` → 2 replicas)
  - cloud: `10.224.0.199:30600` (same proto/service, currently healthy — emr-v2 用作 primary)
    （**2026-09-08 起 `10.224.0.199` 已死，cloud 位址改 `10.224.0.10:30600`**；INCIDENT-20260908）
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
- **⚠ syntheticSuccess（VP-17755 反方發現）**：`sendNotification`（azure-notification-producer.ts:306-348）
  失敗時 enqueue Bull 後回硬寫的 `errorCode:0`——**errorCode==0 ≠ 已送達**，不可當成功判準
  （拿它寫抑制 key 會把「還在重試」變成永久抑制）。
- **failed_notification 只有 writer 沒有自動 retry reader**：寫入 = 給 operator 手動恢復的紀錄，
  不會觸發重寄（VP-17753 的降級紀錄靠此保證不重複送）。
- **去重的真身 = acquireEventLock per-event**（Redis NX 300s + trigger_history 永久 row）；
  per-sample dedup gate 已刪（VP-17755，死碼，writer 從未存在）。eachMessage 外層 catch 吞 throw +
  autoCommit → handler 內任何未接的 throw = 該 event 永久靜默遺失（VP-17753 的失效鏈）。
- **測試陷阱**：spec mock 'src/redis-sentinal'（virtual）蓋不到 `./redis-sentinal` 這種不同 specifier——
  真 ioredis 連線會讓 jest 永不退出；要對兩個 specifier 都 `jest.mock`。
- main / stage_test 不是 promote-forward 對（詳 patterns.md 2026-08-24 條目）；deploy 需要 named
  Entra identity（PR #165，AKS RBAC namespace "setting"）。

### Portal-Calendar（legacy，VP-16499 specialty 追查 2026-07-14；**repo 已 ARCHIVED**，2026-07-15 確認不可 push/PR）
- **Purpose**: legacy portal calendar/clinician service — `/v1/portal/calendar/*/clinicians/first-available` 的真身（**不是** transformer-v2）。consult-reminder 程式碼已遷至 LIS-transformer `src/calendar/email/`（見該 section）；on-prem pods 的 Bull 連不上 redis（無 REDIS_URL）— 別再把 reminder 事故算到它頭上（VP-17421 教訓）
- **Tech**: NestJS + Prisma → MySQL **crm** DB（dev `192.168.10.40:33306/crm`）；prod 跑 **on-prem**（AKS 的 portal-calendar deployments 已 scale to 0 逾 225 天 — 別被雲上物件騙）；repo 另有 schema2 → `va_schedule@192.168.10.213`（此 flow 不用）
- **Key tables**: `clinicians`（+ `clinicians_on_lab_products` → `lab_products`，soft-delete `deleted_at`；`clinician_availability_settings`）+ `calendar`（events）
- **⚠ v2_calendar.specialties drift 根因**：first-available API 回的是「照 availability 過濾後的 derived specialties」— 拿它當 seed source 必 drift。正解是直接讀 crm 表（email lowercase match、full-overwrite + 三向 diff）。**2026-07-14 狀態：整個 service 可能整包遷 v2，等 PM 決定 — sync 不要先做**（見 [[VP-16499]]）。

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

## 【更新 2026-09-11】存取權限備忘
- **LIS-Shipping**（Vibrant-America/LIS-Shipping）：agent GitHub 帳號 `permissions.push=false`，org `allow_forking=false` → 不能開 branch 也不能 fork PR；
  交付 = `git format-patch`（VP-18185 patch 存於 `storage/short_term_memory/VP-18185-lis-shipping-aa65b0b3.patch`）。`LIS_EMR_GRPC_URL` 指向死的 legacy emr port 31316（詳 emr-integration.md 2026-09-11）。
- 跨 repo 計畫前先 `gh api repos/{owner}/{repo} --jq .permissions.push`（同 va-portal 教訓）。emr-v2 `push:true`。

## 【更新 2026-09-18】trans v1 / v2 部署與 CI 邊界
- **LIS-transformer**（v1）：ns `default`，Service `lis-trans-service:3146`，deploy Actions `lis-transformer-deploy-prod`（main）/ `-staging`（stage_test）；**LIS-transformer-v2**：ns `transv2`，Actions `frontend-service-graphql`（main）/ `-st`。兩邊 `ci-tests.yml`（tsc + jest，`needs: [test]` 擋 buildImage）只在 `pull_request` 到 `main`/`stage_test` 觸發 → stacked PR 在 retarget 前無 CI。
- v1 proxy 家族現況（2026-09-18）：`/proxy/grpc/*` 六條（getTestStatus / getQuestionaireBySampleId / listTnpCode 待退，getKitStatus / getPatientTestsResult 有未識別 caller，sendSkinPlacePatientOrders 是 billing 的整併終點）；`/proxy/old-report/*` 11 條只有 `downloadTestOrderPDF` 活著（下游 lis-order，非報告伺服器），與 `trans-reports.controller.ts` 的 `/trans/*` 共用 `OldReportProxyService`。報告家族終點是 `LIS-Report/base-report-server`，`/trans/*` 只是 holding position。
- transv2 `TRANS_PROXY_GRPC_MODE=grpc`（09-16 22:03Z 起）、v1 `TRANS_TIMELINE_KIT_MODE=shadow`（inprocess 被 Leo 否決）。v1 gRPC service_config 自 #792 起真的生效（default 60 s、三個寫入 240 s，retryPolicy 已刪）。

## 【更新 2026-09-24】部署鏈的三個新事實（VP-18355 / VP-18345 / INCIDENT-20260908）
- **lis-backend-emr-v2 Jenkins multibranch 已改 "All branches"**（VP-18355，Leo 09-23 在 UI 改）：release PR 開著時 staging 仍會 build（09-24 #433/#434 首次實證）。之前的 workaround（關 release PR 讓 Jenkins 重掃）不再需要。
- **LIS-setting-consumer**：`main` push 同時觸發 `setting-consumer.yml`（prod）與 `setting-consumer-staging.yml`（staging）；`stage_test` 只觸發 staging。四個 deployment = prod/staging × cloud/`-local`，各吃自己的 ConfigMap（`lis-setting-consumer-config` / `-st-config` / `-local-config` / `-local-st-config`，ns `setting`，`envFrom` → 改 CM 必 restart）。gRPC 直連受 `SETTING_GRPC_MODE` + `SHIPPING_RPC` + `TEST_RESULT_RPC` 三 key **成組**控制（`grpc.options.ts` 預設值寫死 prod 位址）；09-24 現況 staging `-st` = grpc、其餘 = proxy。
- **emr-v2 gRPC 位址來源**：AKS `lis-emr-v2-config-prod`（ns emr-v2）是 source of truth，`Jenkinsfile:147,150` export 後 apply 到 on-prem；repo yaml 不被套用。v2 預設在 PR #433 改為 internal LB `10.224.1.113:80`（`v2Endpoint()` 配對 host/port）；v1 cloud 預設 `10.224.0.10`（lis-core-grpc :30276 / lis-test-connect :30600 **沒有** internal LB）。

## 【更新 2026-09-28】trans ↔ emr-v2 第一條相依、雙軌 PR、generated 檔、平台記錄表（VP-18402 / VP-18404 / VP-18032）
- **LIS-transformer（v1）**：`main` / `stage_test` 雙向分岔（09-25：165 / 105），PR 慣例 = 同一改動兩條分支兩個 PR（`{name}` → main、`{name}-stage` → stage_test）；`prisma2/generated/client2/` **在版控中**且 `npm install` 會重生 → 絕不 `git add -A`；ConfigMap `lis-trans-config`（162 key）/ `-st`（165）的真正 apply 來源不在 repo（`lis-trans-k8env.yml` 只有 5 key），加 key 用 merge patch + rollout restart；deploy Actions `lis-transformer-deploy-prod`（main）/ `-staging`（stage_test）成功即上線。本機沒裝 `@azure/event-hubs` 時 `src/utility` 7 個 suite 不會跑。**自 VP-18404 起 trans 會呼叫 emr-v2**（`src/trans/emr-integration-deactivate.ts`，`EMR_V2_BASE_URL` 含 `/api/v1`）。
- **lis-backend-emr-v2**：gRPC v2 client 現在 **6 個**（customer / patient / sample / sales / setting / **clinic**，`GRPC_V2_CLINIC_HOST/PORT`）；新表 `platforms` + `platform_public_keys`（prod 09-28 手動套用，0 列）；`PLATFORM_PUBLIC_KEYS` env 已退役；新端點 `PATCH .../deactivate-clinic-member`（宣告在 `:id` 之前）；hl7 新 terminal failure class `provider_not_in_clinic`。Jenkins 狀態看 commit status `continuous-integration/jenkins/branch`；prod pod 09-28 在 8c99cde（#438），staging 9fec7d0（#439）。
- **可觀測性**：emr-v2 無 exception filter log、無 SentryGlobalFilter、無 request id（VP-18400）；trans pod 啟動 30 s 後固定一則 ioredis ETIMEDOUT（疑似既有）。

## 【更新 2026-09-29】LIS-Sample 部署與權限、transv2 stage_test 缺口、setting-consumer 設定、trans 兩 repo 的 CI 護欄現況（VP-18480 / VP-18466 / VP-18462 / VP-18449 / VP-18456）
- **LIS-Sample**：NestJS 9 + nestjs-pino（`LoggerModule.forRoot`，autoLogging false，`LoggerMiddleware` 全路由除 /healthcheck，已有 x-request-id）；Sentry middleware 已對 JWT 做未驗證解碼取 user context。部署 Jenkinsfile：`master` → prod、`dev` → staging，PR 慣例一個 base 一個 PR（VP-17797：#183 dev + #184 master）。~~**agent 對 LIS-Sample 只有 pull**——改動只能出 patch 給 Leo / committer（Michaelzbchen、Zhibin、Ray）。~~ **【作廢 2026-10-13】`gh api repos/Vibrant-America/LIS-Sample` → `permissions.push: true`，master 無 branch protection；#208/#210/#212 都是 agent 自己的 PR。只剩本機 push gate 的環境問題（node 22 + `npm ci --ignore-scripts`，見 patterns 10-13）。**
- **LIS-transformer-v2**：`stage_test` 與 main 分岔 53/45，靠週期性「Merge stage_test to main」PR 同步；proxy gRPC 路徑（#629）從未進 stage_test，st image `9c54a17` = stage_test head 09-25。`lis-transv2-config-st` 沒有 `TRANS_PROXY_GRPC_MODE`，`SHIPPING_RPC`/`TEST_RESULT_RPC` 指死掉的 on-prem `192.168.60.6`；正確 st 值 = `lis-shipping-service-staging-grpc.shipping...:63142` / `lis-test-connect-staging-grpc-service.results...:6889`（trans v1 st 09-23 起已用）。
- **LIS-setting-consumer**：兩個 deployment `lis-setting-consumer`（envFrom ConfigMap）與 `-local`（+ `lis-setting-consumer-local-secret`），image 3c0a8bb（含 #179/#180，`grpc.options.ts` 已無 prod 預設位址）；prod 09-29 18:17Z 起 `SETTING_GRPC_MODE=shadow`；`-local-st-config` 三個 key 都還沒有。Kafka `kafka.consumer.crash`（`Cannot read properties of undefined (reading '0')`）每天都有、與 deploy 無關（VP-18453 / VP-18471）。
- **in-cluster 服務位址表（prod）**：base-report `lis-base-report.report:30800`（staging `-staging:30801`，transv2-st 用 `-dev:30802`）、shipping `lis-shipping-service.shipping:16256`、accounting `lis-accounting-service.bkkeeping:8084`、charging `lis-charging-service.charging:8084`、samples `lis-sample-service.sample:16300`、order `lis-order.default:4242`、interactive-report `lis-interactive-report.report:30900`、oauth `oauth-service.oauth:8000`、trans 自己 `lis-trans-service.default:3146`、pdf engine `report-pdf-engine.report:80`、shipping gRPC `lis-shipping-service-grpc.shipping:63142`、test-connect gRPC `lis-test-connect-grpc-service.results:6889`。
- **trans v1/v2 CI 護欄**（dream 09-29 從 GitHub 驗）：`ci-tests.yml` 在兩 repo main 上、每個 PR 都跑（09-29 當天 v1 三次、v2 一次全綠）；但 main 的 ruleset `required_status_checks` 仍是 `[]`——紅的 check 只是建議，merge to main 就是 deploy。補上 required check 是 VP-18456，需要 repo admin（agent `admin:false`）。
- 兩 repo 的 cloud-proxy 相關：`default/lis-trans-config` 是叢集裡唯一含 cloud-proxy URL 的 ConfigMap（14 個死 key，09-29 已刪）；`LIS-backend-billing ProZOrderServiceImpl.java:115` hardcode `www.vibrant-america.com/lisapi/v1/lis/cloud-proxy/`，打的是 on-prem 實例不是 AKS。

## 【更新 2026-09-30】results-grpc 的 token 攔截器實況、emr-v2 的 OAuth2 caller 與部署鏈、on-prem test-connect 已不健康（LIS-7882 / VP-18320 / VP-18463 / VP-18466）
- **LIS-backend-results-grpc（cloud prod image = main `efdf8a2`）`MetadataLoggerInterceptor`**：沒 token → 放行 + warn `gRPC missing token`；有 token 但解不開／驗不過 → `RpcException(Unauthorized)`（client 端看到 code 2 UNKNOWN `Invalid authorization token`）。`selectJwtKey`：HS256 用共享 `JWT_SECRET`、RS256 用 `JWT_RS256_PUBLIC_KEY`。**空的或過期的 Bearer 比沒有 Bearer 更糟**。VP-18528 之後的 blocking 只擋「metadata 與 token payload 都沒有 service-name」的 caller；缺 x-request-id 只 warn。攔截器的 log 標題（`gRPC missing token` / `Intercepted gRPC Request` / `gRPC caller identity`）**不進 Datadog**——Yuteng 的 Confluence audit doc（gRPC Caller Metadata Audit，每日 ~17:25Z 刷新）用的是 APM span metadata；要驗 server 收到什麼只能 `kubectl -n results logs` 對 pod（prod 兩個 replica，只有其中一個會有那筆）。
- **lis-backend-emr-v2 呼叫 results-grpc 的 token（LIS-7882，#441 → staging、#440 → main，prod image `9a9fc98` 09-30 18:55Z 起）**：新 `src/modules/grpc/services/oauth2-token.service.ts`（client_credentials，用既有 `OAUTH2_CLIENT_ID/SECRET/TOKEN_ENDPOINT`，prod/staging pod env 都有；5 分鐘到期保護、in-flight dedup、10s timeout、60s 失敗冷卻），`GrpcClientService` 以 `@Optional()` 注入（4 個零參數建構的 spec 不用改），`buildResultsGrpcMetadata()` 供 cloud 與 on-prem fallback 兩個 call site 共用：service-name + `x-request-id`（randomUUID）+ `authorization`（拿得到才附；拿不到 = 省略 + warn 計數 `miss #n` + Sentry 10 分鐘阻尼）。`ShortcutService` 自己那套 minting 沒動（Leo 要最小改動）。**emr-v2 的 OAUTH2_CLIENT_ID 在 OAuth service 註冊名是 `trans v2`**（token 解出 internal_user_name "trans v2"、role INTERNAL、internal_user_id 10000）——audit doc 的 token-payload 欄會顯示這個名字，不是 lis-backend-emr-v2。
- **emr-v2 部署鏈**：feature → PR 到 `staging`（Jenkins `LIS-EMR-V2-BACKEND/staging`，commit status `continuous-integration/jenkins/branch`；Jenkins UI 192.168.60.9:9602 本機打不到，用 `gh api repos/.../commits/{sha}/status`）→ release PR `staging → main` 標題就叫 "Staging"（#440 是 09-28 開的長壽 PR，head 跟著 staging 走，Leo 09-30 在 #441 merge 後 11 秒 merge 它）→ Jenkins main → AKS `emr-v2/lis-emr-v2-deployment-prod`（container 名 `lis-emr-v2-prod`，sidecar `redis:7-alpine`）。**rollout 噪音基線**：舊 pod graceful shutdown 時對 sidecar `127.0.0.1:6379` / `::1:6379` 連續 ECONNREFUSED，3 秒內 ~800 行 error（09-30 18:55:43–46Z），之後歸零；跟改動無關。main checkout 常停在別票的 branch → 用 `~/src/lis-backend-emr-v2.worktrees/{ticket}`；commit 用 `core.hooksPath=/dev/null` 繞過 config-yaml-coupling hook 的假陽性（#249–#266 慣例），CJK 檢查手動跑。
- **staging emr-v2 的 runtime config ≠ repo 裡的 ConfigMap 副本**：真正的 `GRPC_TEST_RESULT_CLOUD_HOST` 指 staging test-connect（dd service `lis-test-connect-staging-deployment`），不是本機副本寫的 10.224.0.x；staging 的 `NODE_ENV=production` 所以 service-name 也是 `lis-backend-emr-v2-production`。staging integrations 會被人切 LIVE/非 LIVE（同一批 sample 00:06Z 過、19:00Z 不過），要驗 staging 用 E2E sample 2494299（integration `vp17312-e2e-test-int`）。
- **on-prem lis-test-connect 192.168.60.6:30600**（emr-v2 的 fallback）：跑的是**舊 image、沒有 MetadataLoggerInterceptor**（garbage Bearer 也放行），而且對真實 sample（2555493 / 2641983）一律回 `Internal server error`，cloud 正常——fallback 今天實際上是壞的，別人的服務，Leo 決定要不要開票。
- **LIS-transformer `/proxy/*` 現況（VP-18320 #847/#848、VP-18463 #849/#850，09-30 全部部署）**：13 條（3 grpc + 10 old-report）+ `/proxy/old-report/downloadTestOrderPDF` 共 14 條已 404；`ProxyModule` 只剩 `ProxyController`，`proxy-removed-routes.spec.ts` 用真的 module 釘 `controllers == [ProxyController]` + 14 paths 404。還活著：`/proxy/grpc/getKitStatus`、`/proxy/grpc/getPatientTestsResult`（10-14 之後隨 VP-18463 下）、`/trans/downloadTestOrderPDF`（portal 偶發用）。`proxy.service.ts` 的 `getTestStatus/getQuestionaireBySampleId/listTnpCode` 仍被 `trans.service.ts` 內部呼叫，不能刪。叢集裡已無 `proxy_getteststatus/proxy_getQuestionaire/proxy_getTnpCode` key；`proxy_getkit/proxy_getresult` 只剩 4 張 setting-consumer ConfigMap（VP-18462 step 4）。
- **LIS-transformer-v2 stage_test 缺口已補（VP-18466 #661）**：#629/#637/#659/#628 cherry-pick 進 stage_test，`lis-transv2-config-st` 的 `SHIPPING_RPC`/`TEST_RESULT_RPC` 改成 AKS staging 服務（`lis-shipping-service-staging-grpc.shipping:63142` / `lis-test-connect-staging-grpc-service.results:6889`），3 個 `proxy_*` key 刪除（145→142）；prod `lis-transv2-config` 157→145（含 VP-18461 的 8 個）。transv2-st 曾是 trans v1 st `/proxy/grpc/*` 的最後 caller。
- **LIS-setting-consumer 09-29 晚上三個 deploy（#183 Ray VP-18497 21:34Z、#184 Leo VP-18462 proto 同步 22:19Z、#186 Ray 22:38Z 刪 on-prem Redis 設定）+ 00:13Z `SETTING_GRPC_MODE` shadow→grpc**：Kafka consumer crash/restart 噪音 21:40–00:16Z 全是 rollout；`check order tag` 這條 error 行每天 1.4–2.4 萬行（09-28 起）是既有的，不是這批改動造成。#183 之後 `/trans/downloadTestOrderPDF` 的組織流量歸零（order-summary PDF 改直接從 order-management 下載）——當 positive control 的路由會被別人的 deploy 拿走。

## 【更新 2026-10-02】emr-v2 一天四次 promotion、shipping 的兩個 proto 檔、trans 的 Redis 分流與 on-prem Redis 開始要密碼、agent repo 的 ticket-watch（VP-18589 / VP-18593 / VP-18595 / VP-18596 / VP-18406 / VP-18485 / TICKET-WATCH）
- **emr-v2 release 節奏**：09-30 一天 "Staging" → main 的 release PR 開了四次（#443 6c1cb59、#445 2aeaa20、#447 de3dbf6、#450 8d0838d，10-01 01:35Z），每次 Jenkins `continuous-integration/jenkins/branch` 3 分鐘內 success，prod pod 2 分鐘內滾完。release PR 的 head 就是 staging 當時的 head（#450 = 2ac6b05 = #449 的 merge commit）。**STM 要在 promotion 後補一行**——VP-18595/18596 的 STM 停在「Not promoted to main yet」，dream 10-02 才補。
- **emr-v2 feature branch 的 base**：VP-18589 從 origin/main 切，之後三張（18593/18595/18596）都從 origin/staging 切（前一張還沒 promote）。emr-v2 沒有 stage_test，鏈是 feature → staging → release PR → main。
- **emr-v2 新檔**：`order-intake/core-kit-status.ts`（共用 kit ladder）、`grpc-client.kit-status.spec.ts`；`order-status.dto.ts` 的 `KitBlock` 五欄 + `KitCarrier = 'FedEx' | 'DHL'`；兩份 proto 副本（`src/proto/shipping.proto`、`src/proto-v2/shipping.proto`）都加了 `pickup_time = 5` 與 `GetTrackingDetails`。prod pod 沒有 `GRPC_SHIPPING_*` env → 用 code 預設 host `lis-shipping-service-grpc.shipping.svc.cluster.local:63142`；pod 開機 log 會印兩個 shipping client 都建好。
- **LIS-Shipping（唯讀看過）**：FedEx EDI → Azure Service Bus `handleFedexTrackingUpdates` → `fedex_tracking_updates` + `client_transaction_shipping`（kit_status / current_status / fedex_delivery_date）；raw 事件在 prisma8 `fedex_shipping_status`（PU/DL、delivery_attempt_exception）；DHL 在 `dhl_tracking_events`。`queryKitStatus` 自己組 `Packages.url`（12 碼 → fedex.com，10 碼 → dhl.com），`pickup_time` = 最早 PU scan（LA → UTC）|| po_create_time。
- **LIS-transformer v1 的 Redis 分流**（`src/redis.ts`、`app.module.ts` `buildRedisModuleConfig`、`calendar/redis/redis-options.ts`）：prod（`SERVER_ENVIRONMENT=prod`）**全部**走 Azure `vibrant-cloud-cache.redis.cache.windows.net:6380`（db0）；stprod 的 `src/redis.ts` / RedisModule 走 Azure **db 5**，但 **calendar 模組（Redlock cron + 三個 Bull email queue）在 stprod 走 on-prem `REDIS_ADDR:REDIS_PORT` = 192.168.60.10:6390 且不帶密碼**。
- **on-prem Redis 從 2026-10-01 22:30:58Z 起要求 AUTH**（prod 192.168.60.9:4646 與 staging 192.168.60.10:6390 都是，dream 10-02 從 pod 內 PING 證實 `NOAUTH Authentication required`；staging 的 trans pod 沒重啟就開始噴，= server 端改了）→ trans staging 每小時 ~5,150 行 `[ioredis] Unhandled error event: ReplyError: NOAUTH`（10-01 22Z 到現在 46k+），`/proc/net/tcp` 顯示 9 條 ESTABLISHED 到 60.10:6390。**prod trans 不受影響**（只連 Azure，12 條到 10.224.2.156:6380）。這很可能就是 VP-18485 留下的「Redis 密碼輪替，owner 未知」被某人執行了。其他連 on-prem Redis 的服務（Datadog 看得到的）沒有 NOAUTH。
- **LIS-transformer 09-30 → 10-02 的別人 deploy**：Michael #855/#857（VP-18592 skin-care BatchGetPatients，main 10-01 17:11Z / 19:46Z → prod `b68e011`）、#863（VP-18630 getSetting BatchGetCustomers）、#861（VP-18332 caller service name）、#865（VP-18613 移除 trans gRPC 未用方法）全進 stage_test；transv2 #667（main 0120b6d）、#670/#671（Fan VIB-1781 PNS）stage_test。10-01 17Z 的 trans v1 203 + transv2 115 error 行 = 這批 rollout。
- **agent repo 的 ticket-watch**（PR #52，09-30 merged）：`DailyJob/ticket_watch/{watch_prompt.md, run_ticket_watch.sh, send_report.py, run_send_report.sh, README.md, com.lis.ticket-watch.plist, com.lis.ticket-report-mail.plist}`，`.env.example` 加 `REPORT_SMTP_*`，`CLAUDE.md` 加 `TICKETWATCH_MODEL`。兩個 plist 已 load（`launchctl list`：ticket-watch 最近 exit 1、report-mail exit 2）。`DailyJob/bug_watch` 是從沒 load 過的前身，其母體已被 ticket-watch 的第二條 JQL 涵蓋。報告檔不進 git（與其他 DailyJob 一致）。
- **這台 Mac 10-01 全天與 10-02 白天對 api.anthropic.com 不通**：dream 五次 DEFER（900s 無網路）、ticket-watch 兩天 RUN FAILED；10-02 18:30 PDT 才恢復。

## 【更新 2026-10-03】emr-v2 PH-931 三連的檔案與 PR、staging CM 同步路徑、Jenkins main job（VP-18664 / VP-18665 / VP-18666）
- 改動檔：`grpc.config.ts` 加 v1 `clinic` / `clinicCloud`（reuse GRPC_CUSTOMER_* env）；`grpc-client.service.ts` ClinicService factory + `listClinicCustomerIds` wrapper + `mapPatientDetailsV1` 補 customerId / customerIds；新 spec `grpc-client.list-clinic-customer-ids.spec.ts`（載真 clinic.proto）；`order-list.dto.ts` `OrderListScope`；`order-list.derivation.ts` 純函式 `orderInScope()`；`order-list.service.ts` `listOrders(params, scope)` + `patientLinkedToScope`；`order-status.controller.ts` 從 token 建 scope；`docs/ORDER-PIPELINE.md` §2.9。既有 v2 `listClinicCustomerIds`（grpc-client-v2）刻意不用（staging v2 指 prod core-v2）。
- PR 鏈：#451 → staging（5a65f7e）、#452 stacked（掉進 feature branch）、#454 帶進 staging（9b766f3）、#455 method-name fix（cb6b802，staging pod 10-03 06:11Z）、**#453 staging → main 235b4a5，Leo 2026-10-04 01:44:47Z merge**；Jenkins `LIS-EMR-V2-BACKEND/job/main/311`（http://192.168.60.9:9602 ）。
- staging CM：來源 default ns `lis-emr-v2-config` → Jenkins 每 build 複製到 emr-v2 ns（patterns 2026-10-03）。staging CM `VIBRANT_API_TOKEN` 是 prod secret 簽的（base-report-staging 401 non-fatal）；`ORDER_API_TOKEN_STAGING` 是 dev 簽的、有效。local gitignored `lis-emr-v2-config.yaml`（六月）與 AKS 有 32 key drift，多是 .199→.10 與單邊新增。
- 草稿（agent repo）：`drafts/VP-18665-pm-reply.md`、`drafts/VP-18666-jira-comment.md`（未貼）。

## 【更新 2026-10-06】emr-v2 10-04 → 10-06 的 PR 鏈與 prod image、cloud-local-proxy 的部署方式、on-prem ingress 路由、staging core / base-report / issue-system 的真實接線（VP-18664 / VP-18665 / VP-18666 / VP-18673 / VP-18464 / SANDBOX-SEED-W2W-20261005）
- **emr-v2 PR 鏈（續 2026-10-03）**：#456 VP-18665 peer cache → staging 3691e5b（10-04 02:32Z，agent 自 merge）；#457 release → main **dd88f44**（10-05 00:24Z，Jenkins main #312 success）；#458 VP-18673 → staging ce20f5d（10-05 00:42Z）；#459 release → main **1d12641**（10-05 20:55Z，#313 success 21:06Z）；#460 Yekai `[INFRA]` staging kustomization VIBRANT_API_BASE_URL → base-report-dev-service（10-05 23:18Z）；#462 Yekai VP-18683 redraw_needed（issue type 103 "TNP Sample Type"）→ staging 39c2e5f；#461 / #463 → main **d8f5fda**（10-06 00:40Z，#315 success 00:47Z）；#464 Leo VP-18034 charging ownership-guard 修正 → staging 827126d（10-06 19:29Z，Jenkins pending at dream start）。prod pod 10-06 = `lis-emr-v2-deployment-prod-57fdcdffb-nn2ds` image `:d8f5fda…`（00:45Z，0 restarts）；staging pod `:39c2e5f…`（01:42Z）。`compare main...staging` = ahead 2 / behind 7（#464 + 其 merge）。
- **emr-v2 新檔**：`src/common/report-service-token.ts`（+spec）；`cachedClinicPeerSampleIds()` 在 order-list 路徑；`k8s/environments/staging/kustomization.yaml` 是 staging CM 值的 git 紀錄（prod 不讀）。Jenkins main job：`http://192.168.60.9:9602/job/LIS-EMR-V2-BACKEND/job/main/`（本機打不到，用 `gh api repos/Vibrant-America/lis-backend-emr-v2/commits/<sha>/status`）。
- **base-report 兩個服務**：`lis-base-report-staging`（`/v1/lis/base-report-staging-service`）接 **prod** core `lis-core-grpc-service:30113` + prod results；`lis-base-report-dev`（`/v1/lis/base-report-dev-service`，NODE_ENV=staging）接 staging core + staging results。staging base-report 的 `GRPC_ISSUE_ADDR` = `lis-issue-system-service.issue:30071`（**prod**），staging issue system 在 :30072。
- **staging core v1**：AKS deployment `lis-core-staging`（ns default，NodePort 30282），DB = `lisportalprod2-testdb.mysql.database.azure.com/lis_core_v7`（configmap `lis-core-staging-config`，user lis_core_emr）；是 prod 的 clone（帶 prod 的 order_report_status）。staging order DB 是另一個時間點的 clone（`getOrderPackageAndTest` 只對 2023-09..11 的 sample 200）。
- **cloud-local-proxy**：repo `Vibrant-America/cloud-local-proxy`，`origin/main` 09f5ddf（PR #21 Ray 09-30 退役 getOrderSummaryReportZip）；PR #20（comments-only）仍 open；**PR #22 `feature/leo/VP-18464` 8d675a4 request-log middleware（`src/request-log.middleware.ts` + spec、`app.use` in main.ts）10-06 ~07:00Z 開、19:13Z 仍 OPEN**。無 CI/CD：Jenkinsfile Dockerfile.prod → `192.168.60.9:6004` registry + `ssh yuxuan@192.168.60.6 kubectl rollout restart -n lis`；AKS image `lisportalprod.azurecr.io/vibrant/cloud-local-proxy:latest`，RS `6cd55bd7c5` 150 天沒換（10-04 03:03–03:37Z 的 SIGTERM 是 node rotation）。每個 AKS pod 都有 `FailedToRetrieveImagePullSecret (regcred)` warning（image 已在 node 上才沒事）。jest 在 Node 24 有 5 個 pre-existing ESM 失敗（auth.controller / grpc.* / old-report.* spec）。
- **on-prem 叢集（appserver04 經 ssh leo@192.168.60.5；.6/.7 同密碼拒絕；/home/leo root-owned 唯讀；/tmp、/var/tmp 可寫；無 sudo）**：ns `lis` Ingress `k8s-ingress` `/v1/lis/cloud-proxy(/|$)(.*)` → `cloud-local-proxy-service:3047`、`/v1/lis/cloud-proxy-st` → `:3048`（rewrite `/$2`；`use-forwarded-headers` 寫成 annotation 是錯的，跟 AKS 同一個 bug）；controller `ingress-nginx` ns 單 pod 在 appserver06（1.0.4），Service NodePort externalIPs 192.168.60.4/.5/.6:80。proxy prod pods（2d8qj / glcx9 07-16 起、hphwg 08-29 起）各 39 行 = 只有啟動；-st pod 的 per-request 行 07-16..09-11（全是 `checkIfPersonalizedReportCanBeCreated`，多為 `ECONNREFUSED 192.168.60.77:8081`），09-11 後 0（transv2 staging 09-14 重指）。無任何 on-prem ConfigMap / Deployment / CronJob 引用 cloud-proxy（Consul KV 沒查，無 ACL token）。**capture loop**：`appserver04:/var/tmp/vp18464-capture/capture2.sh`（pid 2165176，2026-10-06 19:15:27Z 起，每 60 s poll + `seen.ids` 去重，`cloud-proxy-access.log` / `heartbeat.log`；舊 follow-mode heartbeat 留作 `heartbeat-follow-mode-until-20261006T1914Z.log`）；可證明的零窗從 19:15Z 起算，最早 30 天 = **2026-11-05**；停：用 script 檔跑 `pkill -f vp18464-capture/capture2.sh`；移除：`rm -rf /var/tmp/vp18464-capture`。appserver04 重開機要重跑。
- **LIS-backend-billing 部署**：Jenkinsfile → AKS `default/lis-order`（5 pods，Datadog `service:lis-order` env productioncloud）+ on-prem `default/lis-billing`（scaled 0/0，`yuxuan@192.168.60.6`）。走 www 公開前端打 cloud-proxy；15 天內 0 次 `sendSkinCareKit`。
- **agent repo 草稿**：`drafts/VP-18666-order-team-ask.md`（給 order team 的 500 問題）、`drafts/VP-18665-pm-reply.md` / `drafts/VP-18666-jira-comment.md`（已貼為 190458 / 190459）。

## 【更新 2026-10-08】trans v1 的 calendar 模組與 Portal-Calendar DB、兩套排程資料、trans ConfigMap batch 3-4 與 core v1 清零、cloud-local-proxy 上了 main、skin-care 路徑收尾、emr-v2 staging 接上 staging shipping、phleb 的地圖服務（VP-18655 / VP-18749 / VP-18460 / VP-18474 / VP-18464 / VP-18730 / VP-18347 / SANDBOX-SEED / VP-17827 / PO-270 / HL7-TRIAGE）
- **LIS-transformer v1 calendar 模組**（`src/calendar/clinician/*`，Portal-Calendar repo 已 archived）：資料在 Portal-Calendar MySQL `clinicians`（9 筆：3 Suzette Garcia、4 Mary Beth Augustine、14 Brooke Ganev、19 Lillie Luu Nguyen、20 Emaline Brown、21 Jason Barker、22 Jessy Dhanjal、23 Dana Filatova、24 Nour Amri）。**不是 Prisma-migrated**（只有兩個 2022 init migration）→ schema 改動走手動 DDL。連線在 ConfigMap `default/lis-trans-config{,-st}` 的 `PORTAL_CALENDAR_DATABASE_URL`：prod `crm@192.168.60.4:3307`（MySQL 5.5.56，utf8_general_ci）、staging `lis_inventory@192.168.60.11:3306`（8.0.44），Mac 直連可用 `/opt/homebrew/opt/mysql-client/bin/mysql`。Ingress：staging `api.vibrant-wellness.com/v1/portal/calendar/staging/*` → `lis-trans-service-st:3147`，prod `/v1/portal/calendar/*` → `:3146`；controller **沒有 auth guard**。Unimod（vibrant-wellness-portal `ClinicialDetail.vue` / `ScheduleService.js`）用 `GET /clinicians/find-all-clinicians` + `POST /clinicians/update-clinician`；va-portal modal 用 `POST /clinicians/first-available`。**`update-clinician` 無條件 soft-delete 全部 availability row，只從 `body.availabilities` 重建**——只送部分 body 會把該 clinician 的 availability 清光（Unimod 都送全 body，所以沒事；已告知 FE VP-18656）。VP-18655 加的 `credentials VARCHAR(50) NULL`（`clinician-credentials.ts` normalizer：去頭尾空白與前導逗號、`®` 保留、51 字 → 400；`!== undefined` 語意：省略=不變、""/null=清空）已在 prod + staging 兩邊 DDL 完成（10-07）。
- **兩套排程資料並存**：舊 MySQL `va_schedule`（`PORTAL_CALENDAR_DATABASE_URL` → 192.168.10.213:3306，prod/st 同一台）的 `sample_event` **自 2026-05-12 起沒有新 row**（20,719 筆，30 天 0）；真正的 booking 在 Postgres `calendar_prod`（staging `calendar_dev_new`）的 `v2_event_accession_claim`（claim 存在 = booked；release/reset 會刪 row；4,115 筆、30 天 436）。trans v1 本來就有 Postgres client（`src/calendar-client.ts` `CalendarPrismaService`，`prisma/calendar.prisma`，env `DATABASE_URL_CALENDAR`，兩個 ConfigMap 都有），但 prisma 沒有 claim model；`event-sync.service.ts` 的 cron 只同步舊 `booked_schedule` → `scheduler_event`。VP-18749（#904 stage_test 2833633 live；#903 main 386e6c3 10-08 19:47Z）：`EventService.getActiveClaimsByAccession` + `event.module.ts` 多一個 provider，`getSamplesEventsInProcess` 改讀 claim；錯誤路徑 byte-identical（undefined → etd 缺、active_event_id null）。`active_event_id` 的唯一消費者是 va-portal `PatientTestAction.vue:32`。
- **trans v1 `default/lis-trans-config` 的 in-cluster 化進度（VP-18460，42 keys 6 批）**：batch 3（10-07 00:00Z，accounting + charging 5 keys → `lis-accounting-service.bkkeeping.svc.cluster.local:8084` 原路徑無 rewrite、`lis-charging-service.charging.svc.cluster.local:8084`）、batch 4（10-08 00:14Z，`getKitStatusV2` / `sample_url` → `lis-sample-service.sample.svc.cluster.local:16300`（ingress rewrite 去掉 `/v1/lis/samples`）、`url_order_summary_new{,_redraw}` → `lis-order.default.svc.cluster.local:4242`（去掉 `/v1/portal/order`））都已切換、每 pod env 驗證、探針 old==new；batch 5 interactive-report（`lis-interactive-report.report.svc.cluster.local:30900`）排 10-09 00:21Z，batch 6（oauth-service.oauth:8000、lis-trans-service.default:3146、report-pdf-engine.report:80）之後；12 個 www keys 保持公開。舊值全記在 STM（rollback = patch 回 + restart）。staging `getinvoice` 仍指 on-prem `192.168.60.6`。
- **trans 對 core v1 HTTP 已清零（VP-18474）**：VP-18152 已把 3/4 call site 改走 core v2 gRPC（adapter `src/setting/list-customer-by-id.ts`、`src/utility/create-patient-v2-request.ts`；transformer #845/#846、transformer-v2 #662/#663）；最後一個 `GET /utility/login` → core v1 `/api/user/login_via_session/`（15 天 0 呼叫、無任何 repo 呼叫）由 #901（main c8baff1，10-08 19:46Z merge，deploy 進行中）/ #902（stage_test 57c9986，st 探針 401 → 404）刪除。ConfigMap 四個死 key（`list_customer_by_id_carlos` / `create_patient` / `create_patientv2` / **`create_patientv2_token`＝永不過期的 admin JWT，user 54674**）10-08 17:02Z 從 prod + st 移除（rollback 值在 `~/src/credential/vp18474-lis-trans-config-removed-keys.txt`）；`LOG_IN_VIA_SESSION` st 已刪、prod 等 #901 部署後刪（cron 9ee7ecb9 10-14 10:07 PDT 做 prod key + 兩週零證據）。core 那邊剩下的 v1 呼叫者是 lis-order Java（list-customer-by-id ~52k/8 d）——Zhibin 的 VP-18156。
- **cloud-local-proxy 現況（VP-18464 / VP-18730）**：AKS `847c103f`、on-prem `f017a0c9`，兩邊都 = main `a419bbd`（#23 request-log middleware + #24 `node:22-alpine` runtime + 5 月的 OAuth2/redis code **第一次上線**）；hotfix `75162fe`（e763720 + middleware，Node 16）兩個 registry 都留著當 rollback（re-point latest + rollout restart）。部署配方：AKS = ACR `lisportalprod.azurecr.io/vibrant/cloud-local-proxy`（admin 帳號在 `default/regcred` .dockerconfigjson；Leo 的 AAD 只有 Reader；`:latest` 用 registry API PUT 移、blob 用 curl 補）+ `kubectl -n cloud-local rollout restart`；on-prem = `docker save --platform linux/amd64` → scp 到 appserver04 `/var/tmp` → `sudo -S`（密碼放 600 檔，ssh 無 tty）`docker load/tag/push` 到 `192.168.60.9:6004` → `kubectl -n lis rollout restart`（leo 可直接跑）。on-prem 兩個 Deployment 的 env 是逐 key `valueFrom`（不是 envFrom），10-08 patch 進 `Azure_redis_host/port/pass` + `OAUTH2_CLIENT_ID/CLIENT_SECRET/TOKEN_ENDPOINT`（configMapKeyRef）。驗證：公開前台 `/` 200、`-st/` 200、帶 JWT 的 `/grpc/listTnpCode` 200 真資料（第二次 0.5 s = cached OAuth2 token）。**-st pods（兩個叢集）每分鐘 ~13 筆 `[ioredis] NOAUTH`**：`redis-client.ts` 在 SERVER_ENVIRONMENT=stprod 用 `192.168.60.9:4646` 無密碼；oauth2-token.ts 吞掉 redis 錯誤所以 -st 能動，但每個 -st gRPC 呼叫 8–10 s——修法在 VP-18730 描述的 follow-up（stprod 分支給密碼或改 Azure redis），Leo 選不另開票。Jenkinsfile 只部署 on-prem（AKS 沒有 CI）；`.harness/first-test-pipeline.yaml` 推的是測試 repo。caller 盤點：Datadog `@event:cloud_proxy_request -@user_agent:vp18464*`（`cf_connecting_ip` 在兩個叢集都是真 caller IP，含 www…/lisapi 前台）從 10-07 22:13Z（AKS）/ 22:38Z（on-prem）起算，最早決定日 2026-11-06；on-prem 不進 Datadog → appserver04 的 capture2.sh（pid 2165176）是耐久紀錄。
- **skin-care 路徑收尾（VP-18347 Done 10-07）**：trans v2 CRM-only（#685 main `719ced3`，`SKIN_CRM_PLACEPATIENTORDERS_URL` 必設、unset 直接 throw；`skin_placepatientorders` 已從 `lis-transv2-config(+st)` 刪除）；trans v1 `/proxy/grpc/sendSkinPlacePatientOrders` 刪除（#885 main `2c14264`，`proxy-removed-routes.spec` 釘住 REMOVED 清單；prod 探針 404）；**trans v1 `/utility/shipSkinCare`（utility.controller.ts:905）仍是活的產品路由**，直接 POST `lis-trans-config.skin_placepatientorders` = CRM——那個 key **不能刪**；setting-consumer 死讀取刪除（#193 main `1be60fe`）。`skin_placepatientorders` 現在只剩 `cloud-local/cloud-local-proxy-config(+st)`（proxy 自己的目標，VP-18465 範圍）與 `default/lis-trans-config(+st)`。LIS-backend-billing 的 `sendSkinCareKit` 自 2025-08-04（07e03c9da，VP-12013）就被註解掉、是死碼（repo 權限 READ）→ 刪除 patch 當 Jira 附件 70612 給 Fangyuan。`lis_frontend_service.skin_care_ship_history` 最後一筆 2026-08-05（月量 174 → 9 → 0），流程本身休眠。staging 沒有 CRM，每個 st config 都指 prod CRM。
- **emr-v2（10-07 → 10-08）**：#466 → staging `8a0efc0`（FHIR PDF proxy：`fhir-public-url.ts`、`fhir-result.controller.ts` 新路由 `GET fhir/DiagnosticReport/:id/pdf`、`fhir-result.service.ts getReportPdf`；ingress `lis-emr-v2-fhir-short-ingress` 的 rewrite 原樣可用；可選 env `FHIR_PUBLIC_BASE_URL` 故意**不**進 CM）→ #467 main `c15bb82`（Jenkins 10-07 18:18Z，prod pod `lis-emr-v2-deployment-prod-cfbbc6b47-q4stq`）。#465「Staging」→ main `75245b4`（10-06 21:24Z）把 VP-18034 的 #464 帶上 prod。#468 `feature/leo/VP-17827`（9d1ab62，practice-level resolve：`services/practice-id-field.ts`、fetcher `practiceId?` 過濾、`practice_not_found` retryable、specs +25）對 **`staging`** open（emr-v2 沒有 `stage_test`，那是 LIS-transformer 的）。**staging ConfigMap `lis-emr-v2-config`（ns default + ns emr-v2 兩份）10-08 18:27Z 加了 `GRPC_SHIPPING_CLOUD_HOST=lis-shipping-service-staging-grpc.shipping.svc.cluster.local` + `GRPC_SHIPPING_CLOUD_PORT=63142`**——staging shipping 服務一直存在（deployment `lis-shipping-deployment-staging`，`LIS-Shipping yamls/cloud-staging.yml`，NODE_ENV=dev，與 prod 不同 store），09-30 起記憶裡的「沒有 staging shipping」是錯的；`grpc.config.ts` 的 staging 預設 host 仍是 `''`（Leo 10-08「先不用」hardening PR；CM 重建後 kit 又變 null 就回來補）。prod lis_emr 讀法：`kubectl cp` 15 行 node 腳本到 AKS prod pod 用 `/app/node_modules/@prisma/client` `$queryRawUnsafe`；raw HL7 archive 在 **on-prem** pod（`ssh leo@192.168.60.5` + expect，要 VPN）。
- **LIS-transformer 10-07 → 10-08 其他人的 main 動作（影響 image SHA 判讀）**：#871 VP-18432 OrderV2、#879 VP-18700 BatchGetSamples、#883 VP-18332 RS256、#887 VP-18488、#893 VP-18490、#875 VP-18701 Postmark token、#897 VP-18725、#888 VP-18432 shadow；transformer-v2 同步 #675/#677/#682/#689/#691/#687/#697。stage_test 另有 #884/#889/#890/#892/#894/#895/#896/#898/#900；每次 merge 都滾 prod/st pods（status:error 的 restart 噪音時段以此對照）。
- **Agent repo**：HL7 triage 的 LangGraph 版在 `DailyJob/hl7_fail/graph/hl7_triage_graph/`（branch `feature/leo/hl7-triage-langgraph`，worktree `.git-worktrees/hl7-triage-graph`，PR #54，venv `~/.venvs/hl7-triage-graph` py3.13 + langgraph 1.2.14；`run_graph.sh` PARALLEL=1 寫 `DailyJob/hl7_fail/graph_out/` 不寄信；`send_triage_mail.py` 共用 ticket_watch 的 SMTP transport；`run_triage.sh` 現在成功/BLOCKED/重試失敗都會 `send_mail()`）；launchd `com.lis.hl7-triage` 仍跑 run_triage.sh；REPORT_SMTP_* 未設 → 任何寄信都 exit 2。10-01..10-07 的 triage 全是 BLOCKED（夜間 VPN 斷）且沒人被通知。
- **Phlebotomy 地圖（不是 LIS repo）**：公開 `vibrant-america.com/blood-draw-maps/v2`（Next.js，`www.vibrant-america.com` 與 `phleb.vibrant-wellness.com` 同一份）→ 搜尋打 `https://www.vibrant-america.com/ps/api/v1/location/search/partial-locations-by-coordinate`（POST）= on-prem NestJS **be-location**（ns `phleb-system-production`，`appserver05`，Cloudflare 前台）；還會打死掉的 `https://zymebalanz.com:8019/api/v1/urls`（domain 現在是 Cloudflare proxy、不代理 8019 → 15 s timeout；新家 `https://phleb.vibrant-wellness.com/app/api/v1/urls`，`/urls/{id}/agency` 已不存在）——只在 `hasSchedules: true` 時觸發。該 namespace 沒有 Datadog、沒有可見 Sentry、本機沒有 kube context；repo 不在 org code-search（phleb repos 都是 jun-zhang2021 的）。Owner：Michael Kingsley（PO-268 的 log 截圖）/ Jun Zhang。

## 【更新 2026-10-09】emr-v2 practice-level 三入口上 prod（VP-17827 #469、VP-18755 #470–#473）、trans v1 ConfigMap 42 keys 收尾（VP-18460）、core v1 HTTP 清零完成（VP-18474）、setting-consumer 四個 deployment 全 gRPC（VP-18462 → VP-18463 10-14）
- **emr-v2 main**：`73e3459`（#469 "Staging" 10-08 22:28Z = #468 practice-level HL7 order resolve）→ `536ad11`（#473 10-09 00:05Z = #470/#471/#472 VP-18755）。prod pods AKS `lis-emr-v2-deployment-prod-558d84ccb4-*` + on-prem `…-df565bbd5-*` 都在 536ad11（00:10Z）。VP-18755 的檔：`result-generation.service.ts`（`validateEmrIntegration(customerId, clinicIds, sampleClinicId?)`、`findDistinctEligibleResultIntegrations` 改排序讓 (customer, sample clinic) 列優先、`getClientConfiguration` 同；`resolveSampleClinicId()` 經 v1 `listSamplesBatch` 取 `order.clinicId`，失敗 → 無偏好 → 舊行為）、`order-intake-enrichment.service.ts`（token clinic 當 practice 傳進 `fetchById/fetchByNpi`，PracticeMismatch → 既有 `provider_scope_mismatch`，API 契約不變）、`result-generation.dry-run-config.spec.ts` mock chain 多一步。log 關鍵字：`[practice]`（result 側）、`[order-intake] provider X has no ordering integration at token clinic Y`（intake 側）、`[practice-id]`（HL7 側）。ConfigMap `ORDER_PRACTICE_ID_FIELD_MAP` **沒有**套到 prod（code 預設含 FOLLOWTHATPATIENT；第二家 vendor 出現再加）。
- **trans v1 `default/lis-trans-config` 收尾（VP-18460 Done 10-08 22:50Z）**：batch 5（interactive-report 5 keys → `lis-interactive-report.report.svc.cluster.local:30900` 的 `/questions-data/…` 與 `/report-data/getResultZoneInOut`）+ batch 6（`OAUTH2_TOKEN_ENDPOINT` / `oauth_url` → `http://oauth-service.oauth.svc.cluster.local:8000/token`、`GET_SETTING_URL` → `http://lis-trans-service.default.svc.cluster.local:3146/utility/getSetting`、`va_events` → 同 host `/events/samples/get-events`、`url_get_product_report1` → `http://report-pdf-engine.report.svc.cluster.local:80/pdf?url=`）10-08 22:47Z 一次 patch；pod 自己經 in-cluster oauth-service 鑄 token、所有上游接受 = 真 round-trip。**最終狀態：147 keys，0 個指 `api.vibrant-wellness.com` / `api.vibrant-america.com`；12 個 `www.vibrant-america.com` keys 保留（skin CRM + 11 個沒有 AKS twin 的 on-prem 服務）**；30/42 移入叢集。10 個舊值在 STM VP-18460（rollback = patch 回 + restart）。探針 `docs/plans/trans-optimization/scripts/vp18460-probes/probe-batches2-6-prod.js`。
- **core v1 HTTP 清零完成（VP-18474 Done 10-08 20:36Z）**：#901 main `c8baff1`（deploy run 37834436573 failed on rollout timeout；#903 `386e6c3` 41 秒後成功且含 #901）；prod `GET /v1/portal/trans-service/utility/login` 404 ×3、control `utility/getSetting` 401；`LOG_IN_VIA_SESSION` 20:03Z 從 prod CM 刪除（148 → 147），rollout restart 後三 pod env 乾淨。Datadog VP-18140 core access log 09-30 01:00Z → 10-08 19:50Z 四條路由 0 筆 trans 呼叫。cron 9ee7ecb9 取消。
- **setting-consumer 四個 deployment 全 gRPC（VP-18462 Done 10-08 22:59Z）**：prod `lis-setting-consumer-config` / `-local-config` 09-30；`-st-config` 09-23；`-local-st-config` 10-08 22:46Z 加 `SETTING_GRPC_MODE=grpc` + `SHIPPING_RPC=lis-shipping-service-staging-grpc.shipping.svc.cluster.local:63142` + `TEST_RESULT_RPC=lis-test-connect-staging-grpc-service.results.svc.cluster.local:6889`（118 → 121 keys）。`proxy_getkit` / `proxy_getresult` 四份 CM 都還在 → **VP-18463 10-14 一併刪**（comment 191289），同一 PR 刪 trans v1 的 `/proxy/grpc/getKitStatus`、`getPatientTestsResult`、`/proxy/old-report/*`（main + stage_test twins）。staging 零計數要排除 10-08 22:47–22:50Z 我們 replay 的 100 筆 401。
- **trans v1 VP-18749 的 prod 證據方法**：`lis-trans-config` 的三個 service token（customer 9708 / 1870 / 27102，clinic 10136，role admin）都 scope 到同一 clinic，找不到有 claim 的 accession → 用 shipped image 內 `.prisma/calendar-client` 直接讀 prod claim（2512016885→13834 等四筆）+ findPatient 前後 total_count 不變、etd 齊全、0 error。工具：`lookup_sample_id` 的參數叫 `accession_id`（反之亦然）、`query_general_sample_events` 回每個 accession 的 customer_id/clinic_id、`lisportal_mysql_query` 是 lisportalprod2 唯讀（`lis_core_v7.sample(accession_id, customer_id)`）；`mysql_query` 的 host lisportalprod 沒有 `hl7_file_input`。
- **LIS-transformer 10-08 → 10-09 其他人的 main**：#906 calendar staging redis → Azure db5（fan-z777）、#899 VP-18737 getSetting → GetCustomerClinicProfile、#908 VP-18754 getPracticeInfo → Core v2、#907 VP-18457 contract snapshot CI；transformer-v2 #700 VP-18751 setAccountInfo、#701 VP-18754、#694 VP-18729 RBAC VIEW→ACCESS、#703 VP-18457。prod trans pods 10-09 又滾了三次（17:14Z / 17:32Z / 18:28Z）。

## 【更新 2026-10-12】emr-v2 Core gRPC auth 雙向上 prod（VP-18770 #474 / VP-18771 #475 → #476 c03e818；prod enforce 10-13 00:22Z）、LIS-Sample 死路由刪除 + log 外洩修（#208/#209、#210/#211）、Phase A 頁與九張家族票、LIS-Shipping 現況（VP-18796）、LBS-1833 prod 資料修
- **emr-v2 main `536ad11` → `c03e818`**（#476 "Staging" 10-12 20:46:59Z，GH Actions run 38306443473 success；prod pod `lis-emr-v2-deployment-prod-5988dbbb6b-v76zz` 00:23Z 重啟後仍 c03e818）。檔：NEW `src/modules/grpc/services/core-grpc-auth.service.ts`（`CoreGrpcAuthService.interceptor()`，RS256 → HS256 → ''，`TOKEN_WAIT_CAP_MS` 3 s，stats misses/fallbacks，Sentry damped 10 min，`onModuleInit` pre-warm，boot 印 `[VP-18770] Core gRPC calls carry the OAuth2 service token signed RS256`）、`oauth2-token.service.ts` `getAccessToken(alg='HS256')` per-alg cache（RS256 多送 form 欄位 `algorithm=RS256`）、`grpc-client.service.ts` `CORE_V1_CLIENTS` set（sample/customer/patient/referenceRange/contact/clinic + Cloud）+ `clientOptions(name)`（testResult*/shipping* 不掛）、`grpc-client-v2.service.ts` 六個 client 全掛、NEW `src/modules/auth/guards/grpc-auth.guard.ts`（`GrpcAuthGuard`，ConfigService-only；`@UseGuards` 在 ResultGrpcController + ReferenceRangeController；log 行 `[VP-18771] grpc_auth_check method= service_name= alg= outcome= enforced= identity= reason=`，outcome ∈ ok / missing_token / bad_alg / key_unavailable / invalid_token / no_identity）、spec `grpc-auth.guard.hybrid.spec.ts` 用真 hybrid app + grpc-js client（fixture `__fixtures__/grpc-auth-test.proto`；nest-cli assets 只 copy `proto/**`）。
- **emr-v2 env**：`CORE_RPC_RS256`（code 預設 on；`off` 關）、`AUTH_GRPC_MODE`（code 預設 log；**prod CM `lis-emr-v2-config-prod` 10-13 00:22Z 設 `enforce`**；staging CM `lis-emr-v2-config` 沒設 = log，因 staging key 不對）。prod 探針（`kubectl port-forward svc/lis-emr-v2-service 15001:5000` + grpcurl `ResultGenerationService/GetResultStatus`）：無 token → `Unauthenticated: missing_token`、假 HS256 → `invalid_token: invalid signature`、真 RS256 → served。Core V2 `token_check` caller `lis-backend-emr-v2-production`：20:56:34Z 後全部 `token_class=service`（dream 01:31Z 複查 43 行；最後的 none 是 20:53:58 / 20:56:34 舊 pod drain）。
- emr-v2 staging `83159c5`（#475 merge = staging head；pod `8fd66f9fb-btqpm` 10-12 18:24Z；staging 的 Push-on-staging 沒有 GH Actions deploy run——image 由別的管線產，看 pod）。
- **LIS-Sample**：master `0a93d8b`（#206 VP-18332 Core RS256 interceptor，Zhibin）→ `3a44ca9`（#208 VP-18480 刪 18 條零流量路由：NotificationsModule、CustomersModule 整個刪、openapi -16 paths、33 files -2,369 行）→ `19fbb0f`（#210 VP-18782 `src/middleware/request-log.serializer.ts` `serializeRequest` / `LOGGED_REQUEST_HEADERS`）；dev `652d3c4` → `031c59f`（#209）→ `9a556cf`（#211）。prod 3/3 pods `lis-sample-prod:19fbb0f5`（23:52–23:53Z），staging `lis-sample-staging:9a556cff`。master 現況：GET /patients/profiles、/patients/pns-jwt、/phlebotomists 沒 guard；GET /patients/resend-tubes（262 calls）沒在 openapi；master pre-existing 紅：7 個 jest suite（5 ESM import、core-oauth.interceptor.spec 6 case、utils.batch-get-samples）+ 5 eslint error——不是我們的。
- **Jenkins `lis-sample`**（192.168.60.9:9602，anonymous 403）：無 webhook；Branch Source 名單 10-12 起 = all branches（Leo 改）；master/dev build 仍要手動 "Scan Multibranch Pipeline Now"，6–10 min 後 image 出現、`kubectl set image` 由 pipeline 做；feature branch 只跑 echo stage（~1 min）給 status 用。
- **LIS-Sample caller 表（Phase A，12.8 d，`@event:caller_attribution`）**：66 route+method 有流量 / 83 openapi op → 19 零流量（18 刪、/healthcheck 排除）；browser 內部 staff 74 人撐 Order / Tests / Tubes / Storage / Record-Management（sample-page bundle 十條各 ~16.8k）；服務：**Shipping Service** `axios/1.15.2` role INTERNAL → `/patients/orders/operation-settings` 14,338（全路由 31,245）+ pns-jwt 11 + tests 27（走 public ingress `LIS_SAMPLE_HTTP_URL`）；**lis.results** → `POST /storage/records/samples/retrieval` 2,170（100 %）；**trans v2** axios bearer 無 user claims → `/patients/v2/kits` 22,858 in-cluster + 9,119 ingress、`/status` 9,503 direct；**trans v1** → v2/kits、status；個人 token 腳本（zichenzheng python/node：storage/records 3,235、tests 1,488；Data team python-httpx：audit-logs、duplicate-check；rui.c curl portal-jwt 46）；**無 token** `GET /patients/profiles` 309 來自 45.24.217.146（lab egress，axios/1.19.0，by accession_id，名字不明）。`direct`（無 x-forwarded-for）= in-cluster。order-management（Go）與 lis-accounting 的 client 零流量（dormant）。
- **Phase A 交付**：Confluence 2727378970（roadmap 2711453698 子頁；v3 10-13 00:05Z 帶票號、v4 01:12Z 加 VP-18612 約束）；home = **trans v1**（Leo「轉到v1」）；九張家族票 epic VP-18260（Task、P2、story points customfield_10016、未指派）：VP-18795 status 8 / VP-18796 service routes 10 / VP-18797 sample-page bundle 24 / VP-18798 patients 10 / VP-18799 order 10 / VP-18800 record mgmt 6 / VP-18801 tests+tubes+logs+coupon+phlebotomists 10 / VP-18802 storage 20 / VP-18803 ingress rewrite + scale-to-zero 5；kits 留 VP-18482（32）。Blocks：18482→18795；18795,18796→18797；18481→18796,18797,18801,18802；18482→18798,18799,18800；全部 + 18482→18803。roadmap §5.3 的連結仍要 Leo / Yekai 補（66 KB 頁，markdown round-trip 風險，沒動）。
- **LIS-Shipping（VP-18796 現況）**：prod 3 replicas `lis-shipping:d6132581`，staging `lis-shipping-staging:5d145259`（dev #479 LIS-7864）；CM `lis-shipping-config-prod` / `-staging` 10-13 加 `SHIPPING_LIS_SAMPLE_MODE=http`；`LIS_SAMPLE_HTTP_URL` prod = `https://api.vibrant-wellness.com/v1/lis/samples/`、staging `/v1/lis/samples/staging/`；`LIS_TRANS_GRPC_URL=lis-trans-service-rpc:3192`（trans_service.proto copy 已過時）；`LIS_TEST_RESULT_GRPC_URL=lis-test-connect-grpc-service.results:6889`（= LIS-Sample 的；從 shipping prod pod tcp 可達）；`AUTH_JWT_SECRET` shipping-secret-prod == sample-secret-prod（sha 6ee45d03）、staging == dev（710816ad）→ 本地鑄的 pns_jwt byte-equivalent。Shipping 消費 LIS-Sample 只用三個欄位：operation-settings `data.contains_hormones`（`orders.hormones.service.ts:2900-2930` retrieveSampleOperationSettings，per sample 序列呼叫）、`/tests` 的 `sample_tests[].test_id` + `test_status==='approved'` vs HORMONE_RELATED_LAB_TEST_IDS（`orders.service.ts:15494-15542`，錯誤吞掉 → editable）、pns-jwt `data.pns_jwt`（`orders.service.ts:18194-18218` sendPnsNyWaiverForm）。LIS-Sample 的來源：contains_hormones = order-service `orderTest/getQuestionnaireRequiredMap`.has_hormone_questionnaire（5-min Redis cache、3 s timeout、`|| false`）；approved = results-grpc `TestResultInfoGrpcService.getTestsResultsRelatedData`（要 bearer，Shipping 的 `createGrpcMetadataClient` 自帶；`sampleId` int32，accession 會溢位；status 詞彙 `approved`）；pns_jwt = HS256 `{patient_id, customer_id, clinic_id, role patient, internal_user_role admin, exp +6h}`。Shipping 已有 `retrieveQnrRequiredMap()`（`orders.service.ts:17582-17618`，同 route）、`LIS_TEST_RESULT_GRPC`（只有 tnp.proto；tests-result-info.proto 同 package `testresult` → 要第二個 provider `LIS_TEST_RESULT_INFO_GRPC`）、`vibrant-oauth2-client` token（order-service 對 emr-v2 的 OAuth2 identity 回 `Invalid CustomerId`，對 Shipping 自己的可以）。patch：`storage/short_term_memory/VP-18796-lis-shipping-af2f0601.patch`（9 files +965/-38，含 `src/orders/lis-sample-direct/` 三檔 + 19 spec）。
- **LIS-transformer 10-09 → 10-12 其他人的 main**：#912 VP-18490 getTimeLine 數字 accession（YFvibrant）、#910 VP-18660 Service Date sort、#913 VP-18432 OrderV2 shadow、#916 VIB-1781 sign-in code email、#918 VP-18729 RBAC VIEW 退役（Michaelzbchen / fan-z777）；stage_test 對應 #911 / #915 / #917 / #919。10-14 VP-18463 的 PR 以這些為 base。
- **prod lis_emr 資料修（LBS-1833，10-12 23:20:23Z，單一 transaction）**：ehr_integrations `c0000CMYCWWC500T3A1A86BHS` LIVE → REJECTED（`last_modified_by 'hung.l@zymebalanz.com LBS-1833'`）、`ehr_integration_status_history` 217、`ehr_integration_notes` 17（RESOLUTION, internal）、`provider_integration_memberships` 295 ACTIVE → REMOVED。dream 01:31Z readback 一致。

## 【更新 2026-10-13】trans v1 /proxy 面清空（VP-18463）、Phase B 進 trans main 但 prod 全關（VP-18481）、emr-v2 HL7-only vendor 欄位上 prod（VP-18824）、LIS-Sample 其實可以 push、LIS-Shipping 那半放棄（VP-18796）、BioInsights 列退役
- **LIS-transformer main**：3c02794 → `106246a`（#927 VP-18463，23:15Z；刪 `proxy.controller.ts` / `dto/proxy.dto.ts` / `proxy-caller-log.interceptor.ts`，`proxy.module.ts` 留 providers 無 controllers，`proxy-removed-routes.spec.ts` 17 條 404；contracts 快照同步）→ `a6b6fae`（#928 VP-18481，10-14 00:09Z：LIS-Sample 三個 MySQL DB 的 6 個 Prisma client、Redis、Service Bus outbox producer + `storage-info-updates` consumer、legacy import cron，全部在 `SAMPLE_CONSUMERS_ENABLED=false` 等旗標後；entrypoint 改 node PID 1 + bounded shutdown）。deploy-prod 38483151872 / 38488520037 皆 success；3/3 pods，`/health` ok，prod 沒有 Service Bus socket（模組 idle）。**stage_test**：`4c46d5e`（#925）→ `affd8e4`（#926），含 #920/#921/#922 的 sample 模組 **開著**，`lis-trans-config-st` 23:57Z 加 `SAMPLE_LEGACY_IMPORT_ENABLED=true`；五個 replay 情境過、一週 soak 中（10-14 09:15 LA 的 legacy import 要看哪個 pod 贏）。
- **trans v1 `/proxy/*` 已經是空的**：VP-18320（13 條）→ VP-18462（setting-consumer 四個 deployment 全 gRPC）→ VP-18463（最後 3 條 + ConfigMap key）。`lis-setting-consumer-config` / `-local-config` / `-st-config` / `-local-st-config`（ns `setting`，prod 與 staging consumer 同在 lisportalprod 一個 cluster）各少了 `proxy_getkit` + `proxy_getresult`（133→131、121→119 ×2），`SETTING_GRPC_MODE=grpc` 8/8 pods；cluster-wide 沒有任何 CM 值提到 `/proxy/grpc` 或 `/proxy/old-report`。prod 3/3 pods 探針：getKitStatus / getPatientTestsResult / old-report/downloadTestOrderPDF 404，control 401。
- **lis-backend-emr-v2 main**：c03e818 → `6aad013`（#479 = #477 code + #478 docs，Leo merge 23:27Z，prod pod 23:34Z）。新欄 `ehr_vendors.result_folder_hl7_only` TINYINT(1) NOT NULL DEFAULT 0（prod ALTER 198 ms、staging 106 ms，部署前套；prod MDHQ id 1 = 1、staging MDHQ id 106 = 1）。`report-pdf-settings.ts` 的 `resolveReportPdfDelivery` 多一個 `vendorHl7Only` 輸入 → 真時回 `{split:false, combined:true}` 蓋過 practice/partner/sibling 旗標；`result-attachment.service.ts resolveDelivery` 讀它並 WARN；`deliverOrderSummaryAttachment` 對 HL7-only vendor 直接 return。docs：`docs/VP-18824-HL7-ONLY-VENDOR-FOLDER.md`。
- **prod `ehr_integrations`（10-13 兩筆資料修）**：Maristany `cms56tk180041t807p7tt9nxm` `split_result_pdf_by_report` 1 → NULL（`last_modified_by='VP-18824'`，17:05 PT；全表 split/combined 非 NULL = 0）；BioInsights `cms3icsz700010xlgywfuj8do`（JAG 30248/132493）LIVE → **REJECTED**、ordering/result_enabled 0（18:31:10Z，`ehr_integration_status_history` 218）。JAG 的 P2P 列 `cmjxaqui500i50xfq4zc5yddg` RESULT_ONLY LIVE 不動。
- **LIS-Sample**：master `c1b3c35`（#212 doc：staging DB 10-13 起已 migrate、LIS-Sample staging 永不 publish、trans-st 代為 drain）→ Jenkins 23:33Z 滾 prod RS 78c8b5b465 3/3；dev `68f15c9`（#213）。**push 權限：有**（見上方 09-29 條的作廢註）。LIS-Sample prod 舊 pod 終止時 readiness refused + Error = 它本來的 non-graceful shutdown。prod queue `storage-info-updates` active 0 / dlq 220（長期不變）、outbox 39,910 / unsent 0 / dead 0。
- **LIS-Shipping**：push=false 再次確認（dry-run 403、org 禁 fork）→ Leo 10-13 01:45Z 放棄 Shipping 那一半（VP-18796 縮成 results 那半）；`SHIPPING_LIS_SAMPLE_MODE` 已從兩個 Shipping ConfigMap 移除、從未部署。Shipping 繼續打 LIS-Sample 的三條路由，之後跟家族票（VP-18797 bundle、VP-18798 patients、VP-18803 ingress rewrite）一起搬。patch 留在 git history `61fd16a4`。
- **project-agent-factory**：#95 `lesson/lis/pid1-explicit-exit`（d941ad6）、#96 canary-waiting-on-third-party（a04f931）都已由 Leo merge；ENGINEERING-LESSONS :85 / :120。
- **vibrant-america-working-agent**：PR #57 `chore/leo/provenance-gate`（02f8fe6）→ `lis-prod-change-gate` Gate 1b：practice/vendor mapping 寫入前要引用來源訊息（thread、sender domain）。


## 【更新 2026-10-15】trans v1 接下四個 LIS-Sample 家族（VP-18796 / VP-18801 / VP-18802 / VP-18482，prod 有 code 無流量）、results-web 已走 trans、emr-v2 Cerbo 三連發上 prod（VP-18833 / VP-18832）、LIS-Sample 有了 GitHub Actions 與 18 條路由還原（LBS-1842）、trans 兩個 repo 的 main 有 required check 了
- **LIS-transformer main**：a6b6fae → `efb5782`（#930 VP-18796 `POST /storage/records/samples/retrieval`，10-14 18:20Z）→ 2594f90 / d648973 / a2ac873 / 65fc0a6（他人）→ `81b3f19`（#943 VP-18801 七條路由，10-15 17:36Z）→ 2889091（#946）→ 471ee7e（#866）→ c1ab562（#932 patient_id/accession_id 非數字直接拒）→ `620fd97`（#954 VP-18482 kits in-process，23:22Z）→ `d9a4e78`（#950 VP-18802 storage racks/records 十條 + #948 import lock warn log，23:57Z）→ 8e190fd（#953 VP-18880，10-16 00:40Z）。12 個 deploy-prod run 全 success。stage_test：fc27684 → 0bc209b → cecdf6d → 74cd7f5 → b6cceb1 → a7a0d4b → 53fa869 → 3300177 → 32a9e70 → 7906b63 → e9851e6 → 7c84104 → c753252 → 90bd98b。
- **trans prod `default/lis-trans-config` 10-14/15 新 key**：`DATABASE_URL_LIS_INVENTORY_MASTER`（VP-18796）、`SAMPLE_COUPON_URL`、`REDIS_URL` / `REDIS_PASSWORD` / `DATABASE_URL_VIBRANT_TRACKING_SLAVE`（VP-18801）、`SAMPLE_LIS_TOKEN_FOR_TRANSFER` / `SAMPLE_ORDER_CLOUD_HTTP_URL` / `SAMPLE_PNS_IMAGE_BASE_URL`（VP-18482）。每次備份在 job tmp `lis-trans-config.backup.<ts>.json`。**仍缺 `DATABASE_URL_VA_INFO_MASTER`（/_SLAVE）** → trans prod `GET /storage/racks/suggestions` 與沒帶 rack_id 的 `POST /storage/racks` 500（Datadog 10-15 17:53Z–00:15Z 三行 prisma "Environment variable not found" = A/B 探針）；**VP-18803 切 storage 流量前必加**。`SAMPLE_CONSUMERS_ENABLED` / `SAMPLE_LEGACY_IMPORT_ENABLED` prod 未設（LIS-Sample 仍擁有 consumer 與 import）。trans prod 現在有 Redis，與 LIS-Sample 共用 username cache key `lis::sample::user:name:by:id:*`。
- **trans v1 在 prod 可呼叫但零流量的 LIS-Sample 家族**（ingress 切換 = VP-18803）：storage retrieval（VP-18796——results-web 10-14 18:44Z 起已改走 in-cluster trans，是唯一真的切了的 caller）、tests/tubes/interaction-logs/coupon/phlebotomists（VP-18801）、storage racks/records 十條（VP-18802）、`GET /patients/v2/kits`（VP-18482，LIS-Sample 端 shadow 0.05）。
- **LIS-backend-results-web**：push=true（Leo 10-14 當場給）；PR #147 `d9a2c2c`（dedicated `SAMPLE_STORAGE_API_TOKEN`、ConfigMap URL 改 trans）10-15 00:06Z merge → results team 00:09Z 直接滾 **prod**（Jenkins + 手動 kubectl，無 GH workflow）；staging 仍是 7 月的 6a044fe → staging mirror 切 trans-st 還在等他們的 staging deploy（`SAMPLE_STORAGE_API_TOKEN` 已預放進 `lis-test-web-staging-secret`）。prod ConfigMap `results/lis-test-web-generation-config` / `lis-test-web-config` 的 `SAMPLE_STORAGE_BASE_URL` → `http://lis-trans-service.default.svc.cluster.local:3146`（10-14 18:44 / 18:46Z）；staging 的 `Order_API_Token` 是 prod 簽的、同時打 prod base-report-service，不能換 dev 簽。repo 的 `deployment/azure/k8s-secret-*-cleaned.yaml` 明文帶 DB 密碼 / Event Hub key / 長效 token。LIS-Sample 的 retrieval 路由 soak 到 **2026-11-13**；cloud 沒有 on-prem caller，可以歸零。
- **lis-backend-emr-v2 main**：6aad013 → `46ddd50`（#481 VP-18833 per-report，10-14 23:53Z）→ `6837e9f`（#483 testHierarchyForReports + shared results，10-15 16:54Z）→ `270f0b2`（#485 VP-18832 always-compress，20:19Z；Jenkins prod 20:22Z pod 6f555c7b87-jm52l）。staging 8fba4ee → b458204 → 99a2b01 → 397902e。on-prem pod 每次跟著滾（約 20 分鐘後）。
- **prod 資料修（10-14/15）**：`ehr_integrations` Maristany `cms56tk180041t807p7tt9nxm` `split_result_pdf_by_report` NULL → 1（10-15 00:10Z，`last_modified_by='VP-18833'`，全表唯一非 NULL 列；回滾 = 設回 NULL）；optimalhealthcare `cmjklwqkn003l0xfe67v5qpdb`（cust 14243 / clinic 25199）`result_enabled` / `ordering_enabled` 1 → 0（10-15 21:54Z，status 留 LIVE；備份 scratchpad `vp18832/ohc-backup-…json`）。`lis_emr.platforms` / `platform_public_keys`：1001 Get Healthy 10-14 17:41Z 插入、10-15 換 PEM（fp 475236c8…；staging 保留舊 d6cec97b…）。
- **LIS-Sample**：master c1b3c35 → `8dc0737`（#215 safety net：jest 綠基線、`contracts/` 快照、`.github/workflows/ci-tests.yml` "typecheck + unit tests"——repo 第一個 GitHub Actions）→ `dc78290`（#217 kits shadow）→ `67a0c55`（#218 LBS-1842 還原 18 條，10-16 00:19Z；prod 3/3 約 00:26Z）；dev 68f15c9 → 2661805 → 113433b → `60ed23e`（#219）。Jenkins：master → prod、dev → staging。main ruleset 還沒 required check（admin 後續）。`lis-sample-config-prod`：`KITS_SHADOW_SAMPLE_RATE=0.05`、`KITS_SHADOW_TRANS_URL=http://lis-trans-service.default.svc.cluster.local:3146/`；dev：rate 1 → trans-st。`docs/openapi.yaml` 是手寫的（59 paths），產生的快照才是真相。
- **GitHub rulesets**：LIS-transformer 與 LIS-transformer-v2 的 `main` 現在 required `typecheck + unit tests`（VP-18456 Ethan 10-14 Done；10-16 `gh api repos/…/rules/branches/main` 驗過）。LIS-Sample 無。
- **LIS-Report base-report-server**：`GET /result/testHierarchyForReports`（靜態目錄、barcode 只在 prod 縮「哪些 report」、key = 顯示標題）vs `testHierarchyForInternalReports`（barcode 專屬 id、一次一個 type）。不存在 "getReportTestHierarchy" 路由。
- **vibrant-america-working-agent**：#58（outbound placeholder guard hook 接線）、#59（`vendor-email-reply` skill + `reference/partner-specs/` + gap table）、#60（agent-improve：scoring DF 過濾、dream fallback、`memory-health.py`）皆 merge；factory #97（placeholder hook）、#98（push-guard repo 解析）merge。

## 【更新 2026-10-17】trans v1 再接 LBS-1842 五條還原路由與 VP-18889 notifications/customers（29 條 Sample 路由零流量、caller 文件 + 2026-10-30 deadline）、VP-18801/18802 重開再關、VP-18673 Dev Complete、VP-18800 開工
- **LIS-transformer main**：620fd97 → … → `9912cbf`（#958 Michael VP-18473 / VP-18472，10-16 18:01Z）→ `ab5b67c`（#960 LBS-1842 五條還原路由，20:25Z，deploy-prod 38962136357 ✓）→ `722bf27`（#961 VP-18889 notifications ×4 + customers，20:31Z，deploy-prod 38962864200 ✓；RS 869654cb45 3/3，最終 image 722bf27）→ `b75b5ee`（#964 Michael VP-18458 config-drift，22:27Z）→ `1b4a64f`（#966 YFvibrant npm audit fix，10-17 00:29Z；`config-drift` workflow 首跑 10-17 16:07Z success）。stage_test：9472756（#959）→ a2339d1（#962）→ `71d903b`（#963）。
- **trans v1 可呼叫的 LIS-Sample 路由現在 29 條**（trans main openapi 的 Sample* tags）：VP-18796 / VP-18801 / VP-18802 / VP-18482 家族 + LBS-1842 五條（`GET /interaction-logs/:id/details`、`POST /interaction-logs/resolution`、`PUT`/`DELETE /storage/racks/samples/tubes/:idx`、`POST /storage/records/batch/removal`）+ VP-18889 五條（`GET /notifications/active`、`POST /notifications`、`PATCH`/`DELETE /notifications/:id`、`GET /customers`）。全部零流量；切換 = caller 改 base URL（公開 `/v1/portal/trans-service{,-st}/<path>`）或 VP-18803 ingress。還沒搬：record-management 14 條（VP-18800，進行中）、VP-18798。
- **Confluence 2737373187**「LIS-Sample routes now served by trans v1: what callers change (before / after)」在 Leo 資料夾 2119335937（space 1566212117）；v2 deadline **2026-10-30**。Slack 公告 Leo 10-16 21:10Z 發。之後看 LIS-Sample `caller_attribution` 29 條趨零才動 ingress／刪除（五點規則）。
- **trans prod 仍缺 `DATABASE_URL_VA_INFO_MASTER` / `_SLAVE`**（boot warning 三項之一，另一項 Service Bus key）；VP-18803 搬 storage 流量前必加（#950、#960 的 PR body 都標了）。
- **Jira**：VP-18801 / VP-18802 10-16 18:05Z 重開（scope comment 192453 / 192454 把還原路由納入）→ 21:05Z 再轉 Dev Complete；VP-18889 新票（parent VP-18260，3 SP）同時 Dev Complete；VP-18798 192455、VP-18800 192456 scope comment。LBS-1842 本身在 Reopened（Fangyuan 的票，等 Support 真的 resend）。VP-18673 10-16 23:56Z Dev Complete（code 10-05 起在 prod，Datadog 7 d：585 次 mint 成功、0 次 401）。
- **`runbooks/lis-sample-route-migration.md` + CLAUDE.md Git 規則**：每次 route migration 的固定流程（port verbatim → staging A/B → Leo merge main → prod 唯讀 A/B + 公開 ingress 探針 → Dev Complete + comment → Confluence caller 文件 → Slack 兩週 → 零流量後才動 ingress）。
- **VP-18800 開工（10-16 17:00）**：worktree `~/src/LIS-transformer.worktrees/vp18800`，`feature/leo/VP-18800` off main b75b5ee，未 push；record-management 14 條；7 天 prod 流量集中在 `providers/:id/{patients,samples,clinics}`、`providers/search`；`merge-patients` / `patients/search` / `order-total` 零流量；transfer-all-* 各 1 次 401（LBS-1842 探針）。
- **Datadog 10-16 → 10-17 trans prod**：deploy 後無新 error class；baseline 仍是 ioredis ETIMEDOUT 關機噪音 + `[getRequest]` 下游 404。

## 【更新 2026-10-18】VP-18800 record-management port 完成到「等 #967 merge」；stage_test → 8baccf1
- **LIS-transformer stage_test**：`71d903b`（#963）→ `8baccf1`（#968 VP-18800 stage twin `feature/leo/VP-18800-stage` 84840ec，agent 自 merge 10-17 16:40Z，deploy-staging 39050409022 ✓，trans-st image 8baccf1）。main 仍 `1b4a64f`；**#967**（`feature/leo/VP-18800` f643aff → main）開著等 Leo merge。其他 open PR 不變：#965 Michael VP-18458、#947 VP-18860、#878/#877 VP-18702、#730 VP-18022。
- **VP-18800 port 內容**：`src/sample/record-management/*` + `protos/sample/lis-core/{customer,address,contact,sales,setting}.proto`；新 gRPC client `SAMPLE_CORE_V1_CUSTOMER_GRPC`（CORE_RPC_STAGE，同 SAMPLE_CORE_V1_GRPC）；PatientService 重用 trans `lis_main.proto`（wire-identical）；**無新 env var**。jest src/sample 33 suites / 715 green。
- **RBAC 開關的環境判準不同**：LIS-Sample 只在 `NODE_ENV==='prod'` 時 enforce 14 條 permission（prod pod `start-CLOUD:prod`、staging `start-CLOUD:dev`）；trans 兩個環境都是 `NODE_ENV=prod`（lis-trans-config 與 -st 皆然），所以 port 改用 `SERVER_ENVIRONMENT==='prod'`（prod `prod`、st `stprod`，兩個 ConfigMap 都查過）。之後任何「只在 prod 生效」的 trans 邏輯都要用 SERVER_ENVIRONMENT，不能用 NODE_ENV。
- **Staging A/B 49/49 equal**（A = LIS-Sample staging svc 16399、B = trans-st 3147、dev-signed lis.results 69154）：9 條 GET 帶真資料 + paging/filter/unknown id/非數字 400/401 + 6 條 POST 的 validation 與 same-id 400（six write routes 都在 gRPC 前先擋 same-id）→ 零寫入。**staging 真寫入（merge-patients、5 條 transfer）沒做**：Leo 10-17「剩下的等merge 後再測」。#967 merge 後的清單：prod 唯讀 A/B（含 prod-only 403）、ingress 探針、Confluence 2737373187 caller 頁更新、Jira Dev Complete + comment。
- **Leo 10-17 指令**：subagent 一律跑 Opus → working-agent CLAUDE.md PR #61（已 merge，c36b0f68）。

## 【更新 2026-10-19】VP-18800 record-management 已在 prod（#967 merged）；VP-18798 patients remainder 本機建好未 push
- **LIS-transformer main**：`1b4a64f` → `03f43da`（#967 `feature/leo/VP-18800` f643aff，Leo merge 10-18 16:26Z）；deploy-prod 39145000759 ✓（16:26 → 16:43Z，buildImage 約 20 分）；`lis-trans-deployment` image 03f43da 3/3。stage_test 仍 `8baccf1`。open PR 不變：#965 Michael VP-18458、#947 VP-18860、#878/#877 VP-18702、#730 VP-18022。
- **VP-18800 prod closeout（10-18，Dev Complete 09:45 PT，Jira comment 192549）**：prod 唯讀 A/B 59/59 equal（A = LIS-Sample prod svc 16398、B = trans prod svc 3146）——真資料 reads、所有 400/401、以及 14 條路由用 user-1 token 都回 403 "Permission denied: Not granted"（trans 的 prod-only RBAC 首次在 prod 證實）；公開 ingress prod/staging 各 2 路 byte-identical；Confluence 2737373187 v3（29 → 43 條、record-management 進「switch today」）。**沒做（by design）**：寫入路由（merge-patients、5 條 transfer）從未 live 跑過——staging 與 prod 都是 Leo 的選擇；Slack 宣告新路由是 Leo 的；caller 切換與 ingress rewrite 屬 VP-18803。
- **trans prod 10-18 deploy 後 Datadog（dream 10-19 check）**：record-management 路徑零 error / 零 5xx；error class 仍是舊 baseline——boot 期 ioredis ETIMEDOUT、`[getRequest]` 對 lis-accounting 的 400、以及 `TypeError: Converting circular structure to JSON` unhandled rejection（10-04 → 10-18 已有 46 次，與 VP-18800 無關；尚無人認領）。
- **VP-18798 patients remainder（10-18，Dev In Progress）**：worktree `~/src/LIS-transformer.worktrees/vp18798` `feature/leo/VP-18798` head 32143fc，**未 push**。19 條路由（GET /patients、PATCH /profiles、duplicate-check、complete-reports、kits/resend、resend-tubes、portal-jwt、pns-jwt 加 guard、10 條 POST /orders/* 郵件與 QNR 路由、reset-questionnaire 無票認領故併入）；59 files +18.7k（protos/contracts 為主）；jest src/sample 40 suites / 965 green。新 gRPC client `SAMPLE_CORE_V1_PATIENT_GRPC` / `SAMPLE_CORE_V2_PATIENT_GRPC` / `SAMPLE_TEST_RESULT_INFO_GRPC`。
- **VP-18798 等 Leo 決定的四件事**：(1) 新 env key `SAMPLE_SHIPPING_HTTP_URL`（prod `.../v1/lis/shipping/`、st `.../shipping/staging/`）與 `SAMPLE_CORE_HTTP_URL`（僅 v1 fallback）要先進 lis-trans-config / -st——這是 cross-ticket review 10-15 第 1 點「每張票各自撞到的 prod env key 洞」的又一例，這次在 merge 前就列出來了；Kafka 連線字串改讀既有 `Azure_kafka_connection_string_gen`（sha256[:12] 86850d3eba64 = LIS-Sample prod secret），不需新 secret；(2) GET /patients 在 LIS-Sample 沒有 guard（任何 patient_id 回 name/DOB/gender）——要不要加；(3) staging 寫入要不要真跑（PATCH profiles、kits/resend 會寄 kit、reset-questionnaire）；(4) complete-reports 的 prod 身分：LIS-Sample 用 VibrantClient（VIBRANT_CLIENT_ID），trans 用 settingTool.serviceToken()（OAUTH2_CLIENT_ID）→ 下游 record_user_id 會不同。
- **VP-18798 port 的其他事實**：pns-jwt secret trans `listSec()` 的 secretOrKeyProd/Dev 與 LIS-Sample AUTH_JWT_SECRET prod/dev sha256 相同；`PATIENT_UPDATE_CORE_VERSION` 兩邊都沒設 → v2；Kafka 發佈 LIS-Sample 以 NODE_ENV=prod 判斷、port 改 SERVER_ENVIRONMENT=prod（同 VP-18800 的 env-gate 教訓）；`npm install --package-lock-only` 本機 npm 會重寫 500 行 lockfile → 只手改 root deps 一行（同 VP-18481 #920 教訓）。

## 【更新 2026-10-21】emr-v2 prod 5ba4f6c（vendor gate shadow + accessionId 查詢）、trans main 02bc53c、VP-18486 在 stage_test
- **lis-backend-emr-v2 main**：270f0b2 → de221a4（#487 NEXTECH-EMPTY-ORDER，10-19 19:33Z）→ 2c077ff（#489 NEXTECH-ORC-OBR，22:30Z）→ fa14617（#491 VP-18933，10-20 03:24Z）→ **5ba4f6c**（#495 VP-18960 + VP-18931，10-21 18:57Z；AKS + on-prem 192.168.60.10:6004 都上）。**#497（staging → main，只帶 053a744 = VP-18960 last_error 說明）待 approving review。**部署驗證看 Jenkins commit status；GitHub Actions 在這個 repo 只跑 CodeQL。
- **LIS-transformer main**：03f43da → 0773c6e（#969 VP-18798）→ 429a61b（#973 auth metadata fix）→ 18bdd16（#975 VP-18799）→ **02bc53c**（#983 VP-18487 cherry-pick）；之後 VP-18947 與 dependabot（#979/#981/#984）。所有 deploy run success。
- **VP-18486**：#987 → stage_test merged a66f46f（10-21 18:20Z，deploy 39651905758 ✓）；main PR（`bugfix/leo/VP-18486` bc32b11）尚未開。
- **agent repo**：PR #63（`DailyJob/lis_sample_route_removal`）merged 3f8e1aa；launchd `com.lis.lis-sample-route-removal` 已載入。
- **vibrant MCP `mysql_query` 只連 lisportalprod**（`Unknown database 'lis_emr'`）——lis_emr 要用 emr-v2 `.env` 的 mysql2 路徑。

## 【更新 2026-10-22】emr-v2 prod 24f46ca（gate enforce）、trans main 26d26a6（VP-18486）、kits caller 切到 trans
- **lis-backend-emr-v2 main**：5ba4f6c → **24f46ca**（#497 VP-18960 last_error，10-21 20:39Z）。prod ConfigMap `ORDER_VENDOR_GATE_MODE=enforce`（兩個 cluster）。staging 另有 #498 VP-18931 API-only（db4beb3），等下一個 staging → main release。
- **LIS-transformer main**：→ 26d26a6（#991 VP-18486，10-21 22:30Z，deploy 39686968735 ✓）→ #986 dependabot、#988/#990 VP-18947 / VP-18489 / VP-18961、#992 qpdf shell fix（10-22）。
- **kits**：prod `lis-trans-config.getKitStatusV2` 與 `transv2/lis-transv2-config.get_pns_kit_status` 10-22 18:10Z 起指向 `lis-trans-service.default.svc.cluster.local:3146/patients/v2/kits`；LIS-Sample 該路由 organic 流量歸零（剩 Phlebotomist-APP-Backend 經 192.168.60.6 與一個 Jersey/2.30 caller）。transv2 config-baseline PR LIS-transformer-v2#724。

## 【更新 2026-10-26】emr-v2 prod 3f98865、transv2 main 669283a、trans v1 main 96bb7bf
- **lis-backend-emr-v2 main**：24f46ca → 4525ca1（#502：VP-19006 ZKD + VP-18960 retry jobId + VP-18931 403，10-23 22:07Z）→ 478cb4e（#505：VP-19024 + VP-19019，10-24 00:13Z）→ **3f98865**（#508 VP-19008 TTB，10-26 18:00Z）。AKS + on-prem prod 都在 3f98865。部署由 Jenkins 負責。
- **LIS-transformer-v2 main**：→ 08ea18e（#728 VP-19015，10-24）→ 6acbfdb（#732 VP-19003/19011/19009，10-26 18:01Z）→ **669283a**（#735 VIB-1781 PNS，fan-z777，10-26 18:36Z）。GHA `frontend-service-graphql` 全部 success。stage_test 008826e（VP-18990）。
- **LIS-transformer main**：→ 86e83c6（#999 VP-18491，YFvibrant 10-23）→ 3e7333f（#1001 VP-18947）→ **96bb7bf**（#1004 VIB-1781）。stage_test 688ac41（#1010 VP-18795 /status、#1007 VP-18469 index）。main PR #1008（VP-18469）/ #1009（VP-18795）等 Leo。
- **LIS-Sample**：master b8fb61a / dev d71613e（PO-273 CONSUL_TOKEN env）。results-web/-grpc/-core：已沒有 secret manifest，`deployment-secret-policy.yml` 守門（PO-274）。
