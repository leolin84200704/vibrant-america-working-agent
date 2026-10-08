---
id: ticket-routing
type: ltm
category: pm_patterns
status: active
score: 0.1213
base_weight: 0.7
created: 2026-04-22
updated: 2026-09-24
links:
- SANDBOX-SEED-W2W-20261005
- rules
tags:
- routing
- ticket
- pm
summary: Ticket keyword to repo/module routing table
---

# Ticket → Repo Routing

> 根據 ticket 關鍵字判斷目標 repo 和模組

---

| Ticket Keywords | Repo | Module |
|----------------|------|--------|
| calendar, schedule, appointment, Google, Outlook, Zoom | LIS-transformer-v2 | `src/calendar/` |
| GraphQL, patient order, merchandise, PNS | LIS-transformer-v2 | `src/trans/` |
| questionnaire, survey, form | LIS-transformer-v2 | `src/questionnaire/` |
| provider setting, 2FA, Twilio, email branding | LIS-transformer-v2 | `src/setting/` |
| patient variable, encounter note | LIS-transformer-v2 | `src/patientvariable/` |
| role, permission, RBAC | LIS-transformer-v2 | `src/role/` |
| vital sign, BMI | LIS-transformer-v2 | `src/vitals/` |
| HL7, transformation | LIS-transformer | `src/trans/` |
| clinic setting, billing, test ordering | LIS-transformer | `src/setting/` |
| EMR, integration, AutoIntegrate | lis-backend-emr-v2 | `src/modules/integration-management/` |
| sample, order, patient (core data) | LIS-backend-v2-coreSamples | `service/` |
| notification, email, SMS, push | LIS-setting-consumer | `src/setting-consumer/` |
| result ready, shipment, kit, billing event | LIS-setting-consumer | Kafka topics |
| quarantined order, retry_exhausted, replay HL7 order | lis-backend-emr-v2 | `hl7_file_input.retry_num` re-place + `quarantined_orders`（emr-integration.md 2026-09-11） |
| duplicate integration, remove / deactivate integration, provider left practice | lis-backend-emr-v2（data-only） | `ehr_integrations` LIVE→REJECTED via SQL + status_history（LBS-1784 / LBS-1785 recipe） |
| same test twice, DBS twin, mixed collection method (Partner API) | lis-backend-emr-v2 | `order-intake/order-intake-duplicates.ts` + `CatalogMenuClientService` |
| chargeIndicator T, platform pays, payment assertion, X-Payment-Authorization | lis-backend-emr-v2 | `src/modules/platform-assertion/` + order-intake controller / finalizer |
| order summary PDF, requisition alongside result, attachment on SFTP | lis-backend-emr-v2 | `src/modules/result/services/result-attachment.service.ts` + `ehr_vendors.deliver_order_summary_pdf` |
| consult email recipient, To/CC, booking form email, reminder went to wrong address | LIS-transformer-v2 | `src/calendar/shared/consult-recipients.util.ts` + event/reminder services |
| "Sample not found" from Shipping for an EMR order id | LIS-Shipping（agent 無 push 權） | `orders.service.ts validateSampleId`（死的 `LIS_EMR_GRPC_URL`） |

---

## Project prefix → 性質
- **VP-** / **VIB-** — feature/bug ticket（PM 維護，sprint planning）
- **LBS-** — LIS Backend Service **Service Desk** project（Zendesk 自動同步）。reporter 常是 `Zendesk Support for Jira` app account，actual requester 在 description / `customerRequestType` 欄位。多半是 prod 線上 hotfix / data fix，due 通常 ≤ 2 天。LBS-1487 案例：Mingxi 透過 Zendesk 報 "endpoint revert + repush order"

---

## PM AC 解讀慣例（Leo / Vibrant）

- **「no silent fallback」≠ 一定要 throw**：PM 通常希望「失敗有 log/audit 軌跡」即可，warn log + sweep 既有 fallback path 也算 graceful。VP-16416 驗證：Leo 推翻 strict throw 改 `logWarn` + fall through。實作時若 ticket 描述模糊，預設 graceful fallback + warn log，不要直接 throw 中斷 caller。
- **Step 4 呈報格式**：列細節問題時要**同步給出我的 default 偏好**（「以下我採 X，若不同意可調整」），不要只列多選項給 PM 選 — 多選項格式會讓 PM 只答主問題、忽略細節，導致回頭修一輪。
- **Epic 下 ticket dependency 反向是常態**：本應先做的 dependency ticket 可能 due date 在後（例 VP-16165 due 5/8 但其依賴的 VP-16164 due 5/15、VP-16166 due 5/13）。Step 2 一定用 JQL `parent = <epic>` 列出 sibling 全貌，不要只看單張 ticket 的 due date 推斷可獨立交付。
- **Step 4 至少 propose 一個「最小可獨立交付片」選項**：Leo 偏好把 ticket 切成「不依賴任何 sibling 的 thinnest slice」做完先交，剩下 ACs 等 dependency ticket 完成後再補。VP-16165 驗證：原本以為要做完整 4-step cascade，Leo 拍板只做「fallback 替換」一段。呈報 A/B 兩極方案時主動補 C「最小切片」。
- **Leo 偏好 SQL 用 LIS 內部 ID（FK）而非衍生欄位**：例 `ehr_integrations.clinic_id` 優於 `msh06_receiving_facility`。內部 ID 通常有 index、不受歷史回填殘留影響、未來遷移時改名成本低。寫 SQL 時若可選 FK vs 衍生欄位，預設選 FK。VP-16165 驗證。
- **PM 「only X, not Y」→ narrow exclusion of Y, NOT broad inclusion of X**：VP-16612 案例，PM 講 "only providers, not Clinical Team"。我提 `role === 'provider'`（broad inclusion），Leo 改成 `!(practice_id=150105 AND role='clinicadmin')`（narrow exclusion）。差異：我的版本默默把 patient role 也排除掉；Leo 的版本只動 Y、其他角色維持原狀。**rule**: 把 PM 的「排除誰」翻成程式邏輯時，預設用 `!(條件)` 排除 Y，不要用 `=== X` 限制成只允許 X。前者保留 unconstrained 集合，後者會 silently change 未提及的 case。
- **PM 「在 X field 加上 Y」→ 把 Y 嵌進 X 的 VALUE，不要新增 paired field**：VP-16664 案例，PM 講「每個時間 field 加上 timezone」。我提加 `*_timezone` paired YAML field（broad schema change）→ Leo 立刻拒絕 "不能改 yaml file 啊, email template端什麼都沒改"。正解：embed TZ abbrev 在既有 field value 裡（`consult_time: "10:30 AM PDT"`），YAML schema 不動。**rule**: PM 講「加上某資訊」時，預設「enrich existing field's value」，不要「add new paired field」— 後者會被視為改 template/API 的外部 contract。YAML field schema 對 PM 來說 = email template body 的一部分，加 field 就是改 template，需要明確 OK。

- **VP-16163 (EHR Integration V2) epic ticket 的 body/AC 常從 quarantine PRD 段誤抄，title 才準**：VP-16629（title=「approve/reject integration requests」、body 卻整段 quarantine resolution，實際做 ehr_integrations approve/reject）+ VP-16760（同樣 body=quarantine/provisional、AC 寫 resolved_by/resolution_action，實際是 `ehr_vendor_inquiry`「Not on the list」approve/reject）兩例確認。disambiguation 訊號優先序：**title > `split from` issue link > reporter/Leo comment > body**。遇到 body 講 quarantine/provisional 但 title 講 approve/reject，**先信 title、跟 Leo 確認，別照 body 硬做 quarantine**（quarantine 真正歸 VP-16166 + provisional 歸 VP-16168，多半還沒 ship）。

## EMR Integration Tickets 特殊規則

- **"New EMR Integration"** → DB 操作：ehr_integrations + order_clients + sftp_folder_mapping
- **"No results received"** → 先查 `ehr_integrations` 有沒有記錄
- **"Repush results"** → lis-backend-emr-v2 result 推送邏輯
- **"Update vendor list"** / **"Settings EMR vendor"** → `ehr_vendors` 表 + `vendor-management/` module
- **"vendor public/private"** → `ehr_vendors.is_public` 欄位，source of truth 是 Notion EMR Vendor List
- **永遠用 lis-backend-emr-v2**，EMR-Backend 是 legacy

## Provider Portal 前端 repo 對應（LIS-7716, 2026-08-26）

- **provider portal = `va-portal`（現行 Vue app）+ `ehr-frontend`（新版，經 `EhrSettingIframe.vue` iframe 嵌入，beta flag `newVAsetting`）**。兩邊的 settings 元件互為鏡射（va-portal 用 Dialog/ResponsiveButton + data-testid；ehr-frontend 用 BaseModal/Button 無 testid），改一個 UI 常要雙份。
- **`LIS-frontend` 是內部 lab-ops app，與 provider portal 無關**——別把 provider-facing ticket 路由過去。
- Settings 一般走 transformer-v2 `/v2/portal/trans-service`，**但 EHR Integrations（Third-party tab，beta program 22 `auto_emr_integration` gate）直接打 emr-v2** `…/lisapi/v1/lis/emr-service[-staging]/api/v1/integration-management`（useEMRService.js），不經 transformer-v2。
- Leo 對 portal 前端**無 push 權**（va-portal `permissions.push=false`）——FE half 只能出 patch 檔交接；跨 repo 計畫時先 `gh api repos/{owner}/{repo} --jq .permissions.push` 驗權。

## 2026-09-15 新增路由（dream；VP-18270 / VP-18243 / VP-18138 / TRANS-OPT / BIOINSIGHTS）
- **"EMR order 的 kit shipment method 不對 / Ship To Patient vs Supplied by Office"** → lis-backend-emr-v2 `hl7-order-processing/services/customer-detail-fetcher.service.ts` + `parser.service.ts`（`kitDeliveryMethodsFor`）；資料只看 `ehr_integrations.kit_delivery_option`（唯一依據，VP-18270）
- **"報告送到別家診所的 EMR / CHARM misrouting / 收到不是自己病人的結果"** → 先查該 `msh06_receiving_facility` 被哪些 clinic 共用（P1、PHI），圍堵 = `ehr_integrations.status` LIVE→REJECTED；不要抄任何既有列的 msh06（VP-18243）
- **"order summary / requisition PDF 隨 order 或 result 送 SFTP"** → emr-v2 order-time（`ehr_vendors.sftp_order_forms_path`，`order_attachment_records`）/ result-time（`deliver_order_summary_pdf`，`result_attachment_records`）（VP-18138）
- **"trans / portal API 太慢 / p95 / 優化 / cloud-local-proxy"** → LIS-transformer（v1，`/v1/...`）/ LIS-transformer-v2（`/v2/portal/trans-service`）；計畫與量測在本 repo `docs/plans/trans-optimization/`，追蹤票 VP-18276；shipping / interactive-report / core 造成的尾巴不在 trans 範圍
- **"BioInsights / devcom 整合"** → STM `BIOINSIGHTS-onboarding`；vendor 46，尚無任何 order 落地

## 2026-09-18 新增路由（dream；VP-18288 / VP-18303 / TRANS-OPT / BIOINSIGHTS）
- **"vendor 收到的是 Classic 不是 Personalized / report_option 沒生效 / 換了報告樣式還是舊的"** → 先查 `result_transmission_records.integration_request_id` 是哪一列在推，再用 `file_size_bytes` 重建每次推送的 PDF 大小對 `pdf-cache/download/{accession}?style=classic|advanced`（emr-integration.md 2026-09-18）；config 表沒有歷史。通常不 repush。
- **"result push API 504 / manual repush timed out / generate 端點 gateway timeout"** → 先查 rtr + vendor SFTP（推送多半已完成），再談修法；gateway-free 路徑是 on-prem gRPC `192.168.60.6:31317 ResultGenerationService`。`/lisapi` 的 ~90 s 是 origin 切的，owner 未找到。
- **"/proxy/grpc/* 或 /proxy/old-report/* 退役 / 誰還在打 proxy / cloud-local-proxy 拆除"** → LIS-transformer `ProxyController` + `ProxyCallerLogInterceptor`（`@operation:proxyGrpcCaller`），分類與每條端點的家在 Confluence 2697166874，票 VP-18320（due 2026-10-09）。退役證據看 15 天 caller composition，不看零窗口。
- **"BioInsights / devcom 的 order 沒進來 / customer_not_found=Balandan"** → hl7 7126 / quarantine 13：placeholder NPI 1234567，正確 NPI 1730269200；重送必須換檔名。下一關 emr_code_not_found（catalog 待 Zhenhe）。
- **"診所新 provider 的 EMR order 沒下 / customer_not_found 但 practice 其他人正常"** → quarantine 11/12 樣態（NPI 在 ehr_integrations 與 core customer 皆 0 筆）→ add-provider playbook（`emr-order-customer-resolution` skill），需人決定；quarantine 會到期。

## 2026-09-24 新增路由（dream；VP-18194 / VP-18342 / VP-18344 / VP-18355 / NEXTECH / QUARANTINE / LBS-1799 / TRANS-OPT）
- **per-report PDF / split PDF / `split_result_pdf_by_report` / `deliver_combined_result_pdf` / `REPORT_PDF` / bookmarkPagePdfDownload / Maristany / PH-907 / SIIR-291** → `emr-integration.md`「per-report PDF 交付」+ STM `VP-18194`（canary 待證據）。
- **Nextech / ATCA / Alzheimer's Treatment Centers / George Moricz / vendor 47 / 965721** → STM `NEXTECH-onboarding`（`unblock_when` = 第一個 .hl7 落地）；QA twin QH-7179。
- **quarantine UI / quarantine API / VP-16167 / VP-16173 / UNKNOWN_PROVIDER / matchPractice / practice integrations sub-tab** → STM `QUARANTINE-ADMIN-API-GAP-20260924` + `emr-integration.md`「Quarantine admin API 缺口」；動工前先開 BE 票（Leo 未拍板）。
- **Partner API 422 patient_not_found / Ways2Wellness / W2W / sandbox 50687 / proto drift / wire type / index out of range** → STM `VP-18342`；vendored proto 同步配方 → STM `VP-18344` + `patterns.md`「vendored proto 同步配方」。
- **Jenkins multibranch / staging 不 build / "This project is currently disabled" / release PR** → `patterns.md`「emr-v2 的 Jenkins multibranch」（VP-18355 已修為 All branches）。
- **setting-consumer gRPC 直連 / `SETTING_GRPC_MODE` / shadow / `SHIPPING_RPC` / `TEST_RESULT_RPC` / VP-18345** → STM `TRANS-OPTIMIZATION-20260911` + `patterns.md`「會動的錯誤預設值」；prod 仍 proxy mode、無 open 票。
- **old-report 路由退役 / VP-18320 / VP-18346 / 公告 / 09-30 移除 / `com.lis.proxy-old-report-removal`** → STM `TRANS-OPTIMIZATION-20260911`、`DailyJob/proxy_old_report_removal/README.md`、runbook `vp18324-proxy-pdf-route-cutover.md`。
- **Clinical Consult 六個月 / six-month window / manual consult booking / LBS-1799 / SIIR-312** → `emr-integration.md`「Clinical Consult 六個月窗是 FE-only」+ STM `LBS-1799`（LBS 票走 Atlassian MCP）。
- **coresamples-v2 dead IP / 10.224.0.199 / internal LB 10.224.1.113 / `v2Endpoint`** → STM `INCIDENT-20260908-grpc-dead-node-ip`（PR #433 已進 staging，#434 待 Leo）。

## 2026-09-28 新增路由（dream；VP-18402 / VP-18404 / VP-18032 / VP-18034 / VP-18372 / VP-18386 / VP-18400 / VP-18406）
- **"provider 移出 clinic 後還能下單 / integration 沒停 / deactivate-clinic-member / provider_not_in_clinic / PH-917 / SIIR-293 / removeCustomerFromClinic"** → `emr-integration.md`「provider 移出 clinic → 停用其 EMR integration」+ STM `VP-18402`（emr-v2 兩半）/ `VP-18404`（trans 呼叫端、`EMR_V2_BASE_URL`）。成功路徑 prod 尚未觸發；QA twin QH-7271 / QH-7275 To Do；FE VP-18403（Siyun）。
- **"chargeIndicator T / platform pays / platforms 表 / platform_public_keys / kid / RS256 / Get Healthy / platform 1001 / unknown_platform / PLATFORM_PUBLIC_KEYS"** → `emr-integration.md`「平台付款的平台記錄落地 emr-v2」+ STM `VP-18034`（VP-18032 併在同一檔）；操作 SQL 在 emr-v2 `docs/platform-record.md` / Confluence 2710732802。收款腿卡 accounting `account_type` enum（VP-18089 第三缺口，Fangyuan）。
- **"EMR push 沒重推 / amended 報告 EMR 還是舊的 / repush after amendment / OBR-25 / 修正報告標記 / JAG 30248"** → STM `VP-18372`（Dev Blocked；前提為假、真缺口是 HL7 從不標 C）+ `emr-integration.md`「EMR push『只推一次』的前提是假的」。
- **"consult 確認信寄錯人 / 提醒寄給別的醫生 / contact_email / calendar_owner_email / carolinafnc"** → `emr-integration.md`「Clinical Consult 確認信寄錯人」+ STM `VP-18386`（同形狀第三張：VP-17759 / VP-17765；PH-908）。
- **"integration-management 500 / auto-integrate/requests 500 / emr-v2 沒 log 沒 Sentry / request id"** → STM `VP-18400` + `patterns.md`「emr-v2 的 500 目前留不下任何痕跡」（修法：global exception filter + captureException + x-request-id，未做）。
- **"Schedule Consult 六個月 / consultationEligible / 資格搬後端 / VP-18406 / VP-18407 / PH-925"** → STM `VP-18406`（Step 4 待 Leo；零額外 upstream call）+ `patterns.md`「trans v1 InitialPatientPageHome 的資料形狀」；FE 三個入口 + inline 重寫見 `emr-integration.md`。
- **"LIS-transformer PR 幾萬行 / conflict / stage_test 跟 main 分岔 / prisma2/generated 進 PR"** → `patterns.md`「LIS-transformer 的 PR 慣例：一個改動、兩條分支、兩個 PR」+「版控中的 generated 檔」。
- **"trans 要打 emr-v2 / EMR_V2_BASE_URL / lis-trans-config 的來源"** → `patterns.md`「`lis-trans-k8env.yml` 不是 apply 來源」+ `repos.md` 2026-09-28。

## 2026-09-29 新增路由（dream；TRANS-OPT wave 1-2 / VP-18460 / VP-18461 / VP-18462 / VP-18464 / VP-18466 / VP-18480 / VP-18485 / VP-18243 / BIOINSIGHTS）
- **"trans 的 public URL 改 in-cluster / api.vibrant-wellness.com → svc.cluster.local / ingress rewrite / probe.js / staging 不是 twin"** → STM `VP-18460`（42 keys 六批，batch 1 prod 已切、2-6 prod 已探針等 09-30）+ `patterns.md`「staging 不是孿生就不是彩排」「in-pod 逐 byte 探針」「ingress rewrite 規則」。
- **"ConfigMap 死 key / cloud-proxy key / 192.168.10.153:8081 / 刪 key 回滾"** → STM `VP-18461`（22 key 已刪、舊值在 STM；Jira 仍 Dev To Do）+ `patterns.md`「ConfigMap 改法」。
- **"setting-consumer grpc shadow / SETTING_GRPC_MODE / SHIPPING_RPC / TEST_RESULT_RPC / grpc_shadow 事件"** → STM `VP-18462`（prod 在 shadow，0 事件，09-30 再看才翻 grpc）。
- **"誰在打 cloud-proxy / ingress access log / Datadog 沒 nginx log / Cloudflare edge IP"** → STM `VP-18464`（blocked：Ray 的 on-prem log）+ `patterns.md`「Datadog 裡沒有 nginx ingress access log」。
- **"transv2 拿掉 proxy http 路徑 / TRANS_PROXY_GRPC_MODE / stage_test 落後 main / GetKitStatusBySampleId"** → STM `VP-18466`（draft #659 → main；stage_test 缺 #629，也卡 VP-18320 的 st twin）。
- **"LIS-Sample 誰在呼叫 / caller attribution / request log / LIS-Sample 沒 push 權限"** → STM `VP-18480`（patch 在 `drafts/VP-18480-caller-attribution.patch`）+ `repos.md` 2026-09-29。
- **"redis_s.ts / trans 開機 ioredis ETIMEDOUT / 明文 Redis 密碼 / config.yaml 含 secret"** → STM `VP-18485`（#843 main / #844 stage_test draft；rotation owner 未定）。
- **"CHARM 回 null ACK / hl7_version / MSH-12 2.3 vs 2.3.1 / CHARM SFTP 沒人取 / practice 沒有 interface"** → `emr-integration.md`「CHARM 的第二個預設值缺陷」+ STM `VP-18243`。
- **"BioInsights 第一筆 order / V00000417 / IN1-2 C 掛 JAG / 153 個 result 沒取 / devcom 回信語氣"** → `emr-integration.md`「BioInsights：第三個檔」+ `leo-working-rules.md` 09-29 + `~/.claude/CLAUDE.md` 對外文字段。

## 2026-09-30 新增路由（dream；LIS-7882 / VP-18320 / VP-18463 / VP-18466 / VP-18462 / VP-18460 / VP-18372 / VP-18485）
- **"emr-v2 打 results-grpc 要帶 OAuth2 token / x-request-id / gRPC Caller Metadata Audit / VP-18411 blocking / Invalid authorization token / trans v2 這個 client 名"** → STM `LIS-7882`（#441 staging + #440 main 09-30 都上；prod 端到端 PASS）+ `repos.md` 2026-09-30「results-grpc 的 token 攔截器實況」+ `patterns.md` 2026-09-30「加 auth 前先探拒絕路徑」。
- **"trans v1 /proxy 路由 404 / 13 條 removed / old-report controller 沒了 / downloadTestOrderPDF 去哪了 / verify-18320.js"** → STM `VP-18320`（Done 09-30）與 `VP-18463`（controller 09-30 已下；剩 2 條 grpc + key 等 10-14）+ `repos.md` 2026-09-30「LIS-transformer /proxy/* 現況」。
- **"transv2 stage_test 落後 / #661 port / lis-transv2-config-st SHIPPING_RPC TEST_RESULT_RPC / -st proxy key"** → STM `VP-18466`（兩半都 Done）+ `repos.md` 2026-09-30。
- **"setting-consumer 切 grpc 了嗎 / SETTING_GRPC_MODE / in-pod replay 224 筆 / proxy_getkit proxy_getresult 何時刪"** → STM `VP-18462`（prod 00:13Z 起 grpc；14 天零窗口到 ~10-14）+ `scripts/vp18462-replay/`。
- **"trans 的 shipping URL 切 in-cluster 了嗎 / inventory_url / shippin_address / batch 3 accounting charging 何時"** → STM `VP-18460`（batch 1+2 prod 已切；batch 3 不早於 10-01 18:35Z）。
- **"JAG 重推 / 8/31 amended / 64.124.9.100:2223 是誰 / jagconsulting SFTP / ehr_vendors id 跳號 / BioInsights 沒取 result"** → STM `VP-18372`（Done 09-30，兩個殘項掛 practice / BIOINSIGHTS）+ `emr-integration.md` 2026-09-30。
- **"lis-trans-config 明文密碼 / lis-trans-secret.yml 含 Turnstile / ConfigMap 改 Secret 提案 / Redis 密碼輪替誰負責"** → STM `VP-18485`（Done；提案草稿 `drafts/VP-18485-configmap-secret-proposal-draft.md`，VP-18458 是 transv2 的同題）。
- **"skin care 訂單直打 CRM / SKIN_CRM_PLACEPATIENTORDERS_URL / shipSkinCare 沒流量"** → STM `VP-18347`（#660 已部署、key 未設 = 仍走 proxy；等 Leo 選 cutover 方式）。

## 2026-10-02 新增路由（dream；VP-18589 / VP-18593 / VP-18595 / VP-18596 / VP-18406 / VP-18243 / VP-18372 / VP-18485 / BIOINSIGHTS / TICKET-WATCH）
- **"GET /orders list 跟 lookup 不一樣 / kit null / placed vs kit_delivered / DELIVERY_EXCEPTION / order_kit_status fallback / sandbox 沒有 shipping"** → STM `VP-18589`（Done，prod `:8d0838d`）+ `emr-integration.md` 2026-10-02；文件 = Confluence 2485977089（v27）+ mintlify（Chris）。
- **"kit.carrier / shippedAt / deliveredAt / pickup_time field 5 / GetTrackingDetails / shipping 第二個 proto 檔 / seq %g 事故"** → STM `VP-18593`（Done）+ `scripts/probes/shipping-kit-status-probe.js`。
- **"READY_FOR_RETURN_SHIPMENT 算不算 delivered / return label 在 PO 時就印 / 874611616610"** → STM `VP-18595`（Done，#448 → #450；prod 實測 2598251 = kit_shipped）。
- **"lookup 沒看 order_cancel_time / list cancelled lookup kit tier / E2E-iaston-valid-110341"** → STM `VP-18596`（Done，#449 → #450）。
- **"consultationEligible / Schedule Consult 六個月搬後端 / stage_test 被 ruichennrobot 重指 / #853 #854 reportPrefer 復活"** → STM `VP-18406`（Done 10-02；FE 契約在 VP-18407、QA 在 QH-7277）+ `patterns.md` 2026-10-02 stage_test 條。
- **"CHARM 2.3.1 必須 / null body 未送達 / 98737 Melissa Jones 再核准 / 7 筆 transport error 重推 / Geyer 維持 REJECTED / 143 筆走 interface 以外"** → STM `VP-18243`（Done 10-02）+ `emr-integration.md` 2026-10-02 CHARM 段；workstream 2/3 要另開票。
- **"季報 Q3 205 sheets / queryReportsReleasedInPeriod / on-prem pod 跑季報 / amended 進哪一季"** → STM `VP-18372`（Done）+ `emr-integration.md` 2026-10-02 季報段。
- **"trans staging NOAUTH / on-prem Redis 要密碼了 / 192.168.60.10:6390 / 192.168.60.9:4646 / calendar Bull queue staging"** → STM `VP-18485`（Done，dream 10-02 加了 RE-CHECK）+ `repos.md` 2026-10-02 Redis 條。修法在 `calendar/redis/redis-options.ts` 的 stprod 分支（給密碼 env 或改走 Azure db 5）。
- **"JAG 問 John Doe 訂單 / devcom 測試單落在 JAG / BioInsights mapping 搬家 / ordering_enabled 要不要先關"** → STM `BIOINSIGHTS-onboarding`（10-02 Leo「done」= 回信已發；等 JAG 正確 mapping）。
- **"ticket watch / 早上九點報告 / agent 當 initiator / REPORT_SMTP / bug_watch 為何沒跑"** → STM `TICKET-WATCH-20260930` + `DailyJob/ticket_watch/README.md`；10-01、10-02 兩天 RUN FAILED（無網路），SMTP 未設。

## 2026-10-03 新增路由（dream；VP-18664 / VP-18665 / VP-18666）
- **"GET /orders?patientId= 404 但 patient 存在 / 0 單要 200 空陣列 / patient not accessible to this account / PATIENT_NOT_FOUND"** → STM `VP-18664` + `emr-integration.md` 2026-10-03。
- **"clinic scope / 同 clinic 兩個 provider / ListClinicCustomersByClinicID / bare list 變慢 2 秒 / peer placerId null / ORDER_LIST_CLINIC_FANOUT / mintlify every order in your clinic"** → STM `VP-18665` + `emr-integration.md` 2026-10-03。
- **"list report_available 但 FHIR registered / VIBRANT_API_BASE_URL dev / base-report-dev-service / sandbox FHIR 沒 presentedForm / 2512106925"** → STM `VP-18666`。
- **"emr-v2 staging ConfigMap 被 deploy 蓋掉 / default ns lis-emr-v2-config / Jenkinsfile L421"** → `patterns.md` 2026-10-03。
- **"listClinicCustomersByClinicId is not a function / proto-loader camelCase / 載真 proto 的 spec"** → factory ENGINEERING-LESSONS（PR #92）+ STM `VP-18665` Failures。
- **"sandbox GET /orders 哪個 pod 服務 / .11 查不到 patient"** → `emr-integration.md` 2026-10-03（AKS staging pod；core 用 gRPC 問）。
- **"PH-931 / QH-7478 / QH-7479 / QH-7480 / #453 release"** → 三張 STM + journal `2026-10-02-ph931-trio`。

## 2026-10-06 新增路由（dream；VP-18664 / VP-18665 / VP-18666 / VP-18673 / VP-18464 / SANDBOX-SEED-W2W-20261005）
- **"base-report-staging-service 接 prod / base-report-dev-service / Yekai #460 / sandbox 回別人 prod 單的報告 / 2610016006 2610016007 / staging core 是 prod clone / 3194 掃 4059 單"** → `emr-integration.md` 2026-10-06 + STM `VP-18666`（Done 10-06；原因在上游資料，已交 Xiaoye）。
- **"peer cache / cachedClinicPeerSampleIds / 60s TTL / bare list 5.26s 冷 0.27s 熱 / #456 #457 dd88f44"** → STM `VP-18665`（Done）+ `emr-integration.md` 2026-10-06。
- **"VIBRANT_API_TOKEN prod 簽 / report time will be empty / mintReportServiceToken / report-service-token.ts / 401 base-report staging"** → STM `VP-18673`（prod 1d12641 10-05 21:06Z；Jira Dev In Progress）。
- **"sandbox 造資料 / M01–M11 / order_kit_status 對應 status / lisportalprod2-testdb lis_core_v7 / GRPC_ISSUE_ADDR 指 prod / kit block sandbox null / in_transit 拿掉 / Chris Yekai"** → STM `SANDBOX-SEED-W2W-20261005`（waiting on shipping / report team）+ `emr-integration.md` 2026-10-06 + `leo-working-rules.md` 10-03→10-06（回覆風格）。
- **"cloud-proxy caller / appserver04 capture / kubectl logs --tail=-1 / ingress log 2.5 天 / PR #22 request-log middleware / billing service:lis-order / 2026-11-05"** → STM `VP-18464`（blocked）+ `patterns.md` / `repos.md` 2026-10-06。
- **"兩個來源吻合但都錯 / 同源 / positive control 要只在 staging 存在的資料"** → `patterns.md` 2026-10-06 第一條 + factory inbox proposal `2026-10-06-agreement-between-sources-sharing-an-upstream.md`。
- **"chargeIndicator T 403 Authentication fails / allSharedPaymentMethods ownership guard / charging #367 / Get Healthy platform 1001 / #464"** → STM `VP-18034`（10-06 bugfix 進 staging，待 work session 補 STM）。

## 2026-10-08 新增路由（dream；VP-18655 / VP-18347 / VP-18464 / VP-18730 / VP-18474 / VP-18749 / VP-18704→LBS-1825 / LBS-1828 / VP-17827 / VP-18714 / NEXTECH / SANDBOX-SEED / PO-270 / HL7-TRIAGE）
- **"clinician credentials / Portal-Calendar DB / MySQL 5.5 DDL / update-clinician 會清 availability / Unimod ClinicialDetail"** → STM `VP-18655`（Done 10-07；FE VP-18656/18657）+ `repos.md` 2026-10-08。
- **"skin care proxy / sendSkinPlacePatientOrders / shipSkinCare / billing sendSkinCareKit 死碼 / Fangyuan patch 70612 / skin_care_ship_history"** → STM `VP-18347`（Done 10-07）+ journal `2026-10-07-vp18347` + `repos.md` 2026-10-08。
- **"cloud-local-proxy 部署 / ACR latest 沒動 / Node 22 / uuid ESM / -st NOAUTH 8 秒 / cloudlocalpremerge-cibuild / Harness / Ray bypass / VP-18730"** → STM `VP-18464`（Dev Complete；30 天窗口到 2026-11-06）+ `patterns.md` / `repos.md` 2026-10-08。
- **"手動約 consult / Emaline Brown / 六個月 / LBS-1825 / LBS-1828 / event 14275 14347 / Pearl Tin / Cleo Tetzloff / 以後直接訂"** → STM `VP-18704`（= Jira LBS-1825）/ `LBS-1828` + `emr-integration.md` 2026-10-08 + `leo-working-rules.md` 10-06→10-08。
- **"active_event_id null / va_schedule 死了 / v2_event_accession_claim / findPatient / consultationEligible 定義不變"** → STM `VP-18749`（#903 main 10-08 19:47Z）+ `VP-18406`。
- **"trans 還在打 core v1 HTTP / login_via_session / LOG_IN_VIA_SESSION / create_patientv2_token / VP-18156 10-31 / 10-14 兩週零"** → STM `VP-18474`（#901 main 10-08 19:46Z）。
- **"Nextech 訂單是空的 / OBR-7 14 位 / isICD9 / NxMsg1 / 2646314 / ATCA 沒付款方式"** → STM `NEXTECH-onboarding` + `emr-integration.md` 2026-10-08。
- **"Prospera practice ID / ORC-17 / Tom Porter / 43262 訂錯 clinic / practice_not_found / ORDER_PRACTICE_ID_FIELD_MAP / emr-v2 PR #468 / 7266 VAREQUISTION471"** → STM `VP-17827` + `emr-integration.md` 2026-10-08。
- **"FHIR PDF link / presentedForm / /v1/report/fhir/{acc}/pdf / 404 report status / M07"** → STM `VP-18714`（prod live c15bb82；Jira Dev In Progress）。
- **"sandbox kit block / GRPC_SHIPPING_CLOUD_HOST staging / lis-shipping-service-staging-grpc / M06 M07 order_report_status / Leo 給 Yekai 的話 / M10 re-seed"** → STM `SANDBOX-SEED-W2W-20261005` + `emr-integration.md` 2026-10-08。
- **"blood-draw-maps / draw site 500 / be-location / phleb-system-production / zymebalanz 8019 / PO-268 PO-270"** → STM `PO-270` + `repos.md` 2026-10-08。
- **"hl7 triage LangGraph / run_graph.sh / claude -p node / triage 沒寄信"** → STM `HL7-TRIAGE-LANGGRAPH`（PR #54）。
- **"frontmatter 只剩 jira_status / reconcile 把 frontmatter 吃掉 / mapping values are not allowed / lenient parse"** → `patterns.md` 2026-10-08 第一條 + dream log 2026-10-08 + PR `fix/dream/frontmatter-lenient-parse`。
- **"trans batch 3 batch 4 in-cluster / accounting charging sample order / batch 5 interactive-report / 12 www keys"** → STM `VP-18460`。
