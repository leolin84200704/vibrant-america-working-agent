---
id: QUARANTINE-ADMIN-API-GAP-20260924
type: stm
category: emr_integration
status: active
score: 0.00
base_weight: 1.0
created: 2026-09-24
updated: 2026-09-24
links: []
relations:
  unblocked_by: []
  blocks: [VP-16167, VP-16173]
  sibling: [VP-16166, VP-17827, HL7-NPI-PRACTICE-MATCH-20260820]
unblock_when: ""
tags:
- vp-16167
- vp-16173
- vp-16629
- vp-16166
- quarantine
- practice-integrations
- unimod-admin
- ticket-hygiene
summary: "VP-16167 / VP-16173 (FE) 要接的 BE endpoint 盤點：quarantine 只有寫入沒有讀取/resolve API 且沒有任何 open BE 票（VP-16629 的 AC 寫 quarantine 卻在表存在前三個月就結案）；practice 不需要新 data model（= clinic_id），但 prod 0 筆 UNKNOWN_PROVIDER，真正缺口是 Step 4 practice 比對太窄。"
---

# QUARANTINE-ADMIN-API-GAP-20260924 — VP-16167 / VP-16173 的 BE endpoint 盤點

> 2026-09-24，Leo 問「VP-16173 + VP-16167 有具體 backend endpoint support 嗎？只要提供讓前端能連的 endpoint」。
> 分析 only，無 code 變更。結論已回報，Leo 指示「先記下來」，尚未動工。

---

## 1. 問題與結論

### VP-16173 [FE] UniMod Admin - Practice Integrations Management Sub-Tab
**有可接的 endpoint。** emr-v2 的 `IntegrationManagementModule` 已在 prod 上線，provider / 單筆 integration 層級的 CRUD、審核、設定全都有。

- Base URL：prod ` https://api.vibrant-america.com/v1/lis/emr-service/{path} `、staging ` https://api.vibrant-america.com/v1/lis/emr-service-staging/{path} `
  （ingress 只把 `/v1/lis/emr-service/(.*)` rewrite 成 `/api/v1/$1`，所以 pod 內的 Swagger `/api/docs` 從外面打不到）
- Auth：`Authorization: Bearer <JWT>`（`JwtAuthGuard`）。**只有 customer/clinic 存取過濾，沒有 role gating**，PRD 要的 Sales Director / TPM / PM 限制要另外做。
- 主力：`integration-management/auto-integrate/requests`
  `GET /`（filter: customerId, clinicId, ehrVendorId, status[], priority[], requestType[], assignedTo[], clinicName, *Npi, contactEmail, startDate/endDate, search, page/limit/sortBy/sortOrder）、
  `GET /search`、`GET /metrics`、`GET /:id`、
  `POST /:id/approve`、`POST /:id/reject`、`PATCH|PUT /:id/status`、`PATCH /:id`、`/report-option`、`/assign`、`/cancel`、`/disconnect`、
  `POST /:id/notes`、`GET /:id/history`、`GET /:id/logs`、`GET|PUT /:id/configuration`、`POST /:id/test-connection`
- 其他：`status-management/:id/{status,notes,history,assign}`、`configuration-management/:id/{configuration,test-connection,test-sftp,logs}`、`vendor-management/ehr-vendors`、`auto-integrate/vendor-inquiries`
- 清單單列 = `ehr_integrations` 整列 + `ehr_vendor` + `ehr_vendor_application` + 最新 1 筆 `status_history` + 最近 3 則 note + `statusDisplay`，外層 `{ data, pagination }`

**真正缺的只有兩項**（不是 data model）：
1. `Awaiting Vendor` 子狀態、`Suspend` 動作 — `ehr_integration_status` enum 只有 PENDING / APPROVED / LIVE / REJECTED，要 migration。
2. practice 層級的聚合清單與 Active/Pending provider counts — 但**不需要新表**，見第 2 節。

### VP-16167 [FE] Quarantine Management UI
**零 endpoint。** VP-16166 只交付寫入（`QuarantineService.capture`）+ 7 天 expiry cron，票裡自己寫明「resolve (no API in this ticket)」。`quarantined_orders` / `resolution_logs` 在 prod 活著且有資料，但沒有任何 controller。

---

## 2. 關鍵修正：practice 就是 clinic_id，不需要 VP-16164 / VP-16168

第一輪我回報「要等 VP-16164（practice data model）與 VP-16168（provisional providers）解凍」，**這是錯的**。Leo 當場反駁後查證：

`src/modules/hl7-order-processing/quarantine/quarantine.service.ts:285-306` 的註解就是我自己 2026-08-25 的拍板：
> 不讀 `practice_integrations`（5/27 凍結的 backfill snapshot、無 writer、之後新增 253 筆整合、83 個會送單的 clinic 沒有列），改讀 `ehr_integrations` 的 clinic-level 列。

實際比對邏輯：
- `matchProvider(NPI)` → `ehr_integrations WHERE customer_npi=NPI AND ordering_enabled`
- 沒中才 `matchPractice(MSH-4)` → `ehr_integrations WHERE customer_id='-1' AND clinic_id=MSH4 AND ordering_enabled`
- 命中 practice 但 provider 沒整合 → `UNKNOWN_PROVIDER`，`matched_practice_id` = clinic_id

所以 resolve 動作可用既有零件組合：`link_existing_provider` = 用現有 integration create 幫該 customer 在已知 clinic 補一列 `ehr_integrations` + 把 `hl7_file_input.retry_num` 補回去讓 worker 重跑（service 註解提到的 operator playbook）。**不需要 `provisional_providers`**——provider 是誰 HL7 裡就有（NPI + name）。唯一例外：該 provider 在 core 連 customer 都不存在，那要先在 portal/core 開帳號，emr-v2 做不到，是 PM/Sales 流程。

---

## 3. 更重要的發現：prod 0 筆 UNKNOWN_PROVIDER

`lis_emr.quarantined_orders` 2026-09-24 全表 14 筆：

| reason | status | 筆數 |
|---|---|---|
| OTHER_FAILURE (retry_exhausted / test_code_not_found) | RESOLVED 8 / OPEN 1 | 9 |
| UNKNOWN_ORIGIN (customer_not_found) | EXPIRED 5 | 5 |
| **UNKNOWN_PROVIDER** | — | **0** |

5 筆 identity failure 的 `matched_practice_id` 全 null。原因：`matchPractice` 只認 `customer_id='-1'` 的 catch-all 列，全 prod 只有 **37 列 / 605 個 clinic**（MDHQ、Cerbo 那類 clinic-level vendor）；其他 vendor 的 MSH-4 送的是 customer_id 不是 clinic id（VP-17827 的 8/20 證據），所以一律落 UNKNOWN_ORIGIN。

`ehr_integrations` 現況（prod 2026-09-24）：1132 列 / 605 clinic / LIVE 1109 / PENDING 7 / clinic-level 37。

**含意**：就算三支 quarantine API 做完、FE 接完，`Matched Practice` 欄位會永遠是空的，`Link to Existing Provider` 沒有 practice 可 link。真正的缺口是 **Step 4 practice 比對太窄**（要用 MSH-4 或 NPI 去 core 反查 clinic），這會動到 order intake 判定路徑，建議獨立一票、獨立 deploy。

---

## 4. Ticket 盤點：這三支沒有任何 open BE 票

epic VP-16163 底下的 BE 票：

| Ticket | 狀態 | 實際交付 |
|---|---|---|
| VP-16165 Identity Resolution Cascade | Done | 已做 |
| VP-16166 Quarantine Data Model & Service | Done | 只有寫入 + expiry cron |
| VP-16629 Approve/Reject API for Integration Requests | Done | integration-request 的 approve/reject |
| VP-16760 Approve/Reject for "Not On List" | Done | 同上延伸 |
| VP-16164 / 16168 / 16169 / 16172 | Inactive | 未做 |

**VP-16629 的 AC 文字寫的其實是 quarantine resolve**（status→resolved、`resolution_action`、link-provider / create-provider、provisional provider 標 registered），但它 **2026-05-20 就結案，而 quarantine 表 2026-08-25 才建立**——那些 AC 當時不可能被實作，是拿 integration-request 的 approve/reject 結案的。所以那三支 endpoint 名義上的擁有者是 VP-16629，實際上從沒被做過，也沒有 open 票在追。

VP-16167 / VP-16173 自 2026-05-27 起 Dev Blocked，Jira automation 要 Zhiheng 填 blocker details，至今空白。兩票的 FE layout 子票（VP-16752 / VP-16754）Dev Complete，backend connection 子票（VP-16753 / VP-16755）Dev To Do。**整個 epic 的票面狀態不能當事實用。**

---

## 5. 待決策（Leo 尚未拍板）

1. 開新 BE 票（或 reopen / clone VP-16629）做 quarantine admin API：
   - `GET  /api/v1/.../quarantine/orders`（filter: reason, status, clinicId, 日期；分頁）
   - `GET  /api/v1/.../quarantine/orders/:id`（含 parsed HL7；欄位都已在 row 裡）
   - `POST /api/v1/.../quarantine/orders/:id/resolve`（`{action: link_existing_provider | rejected, customerId?, reason?}`）
   estimate 約 0.5–1 天含 spec 與測試。
2. Step 4 practice 比對放寬 — 另開一票，不與上面同時 deploy。
3. `Awaiting Vendor` / `Suspend` enum migration（VP-16173 用）。
4. 我提議但未執行：起草 VP-16167 / VP-16173 的 Jira comment（盤點 + 可用 endpoint 清單給 Zhiheng）與新 BE 票描述。

---

## 6. Lessons Learned

- **票面狀態 ≠ 能力現況**：我用 VP-16164 / VP-16168 = Inactive 推論「FE 要等前置」，但那兩張票早在 8/25 就被我自己的實作決策繞過了。能力問題要問 code，不要問 Jira。
- **PRD 命名的實體 ≠ 實作需要的實體**：PRD 講 practice_integrations / provisional_providers，我就去 grep 那兩張表，grep 不到就報 blocked，沒問「現行 code 用什麼代表 practice」。
- **打開的檔案要讀完關鍵函式**：`quarantine.service.ts` 我只讀到 line 60 的 header 就去回答，答案在同一檔案 line 294 `matchPractice()`，註解第一行就是我自己寫的結論。
- **查到的數字要用來反問，不是只用來佐證**：第一輪就查出 0 筆 UNKNOWN_PROVIDER，卻只拿它證明「表有在寫」，沒問「為什麼一筆都沒有」——那個數字直接指向 Step 4 比對太窄，第一輪就該發現。
- 呼應常駐的 `Verified means live, not mock`：schema 宣告與 Jira 狀態都是靜態宣告，不是 live 行為。
