---
id: ticket-routing
type: ltm
category: pm_patterns
status: active
score: 0.1126
base_weight: 0.7
created: 2026-04-22
updated: 2026-09-18
links:
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
