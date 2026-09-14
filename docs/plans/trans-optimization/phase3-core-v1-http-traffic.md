# Phase 3.1 — trans v1 / v2 對 core v1 HTTP API 的實際流量量測

- 資料來源：Datadog Logs（`@event:core_v1_http_request`，VP-18140 於 2026-09-10 上線）+ Datadog APM spans
- 查詢時間：2026-09-11 23:05–23:20 UTC（下列數字皆為當時快照）
- 觀測窗口：**2026-09-10 19:22:01 UTC → 2026-09-11 23:12 UTC，約 27.9 小時**（log 第一筆即 09-10 19:22Z，再往前沒有資料）
- 範圍：read-only。未改任何 repo / config，未發 Jira / Slack。
- 相關：PLAN.md Phase 3、VP-18140（request log）、VP-18156（core v1 HTTP surface 2026-10-31 刪除）、VP-17348（epic）

---

## 0. 結論速覽

| Route（core v1 HTTP） | trans v1 (`lis-trans-deployment`) | trans v2 (`lis-transv2-deployment`) | 非 trans 呼叫者 | 判定 |
|---|---|---|---|---|
| `GET /api/clinic/list-customer-by-id/:clinic_id` | **LIVE**：448 req / 27.9h（09-11 整天 389） | **LIVE**：19 req / 27.9h（09-11 整天 13） | `lis-order`（Java/Spring）約 9,000 req / 27.9h；`python-httpx` 一次性 1 筆 | **live from trans（v1、v2 皆是）**；route 本身因 lis-order 而不能刪 |
| `POST /api/patient/create-patient-new` | 0 | 0（v2 無此 code path） | `lis-order` 18 req / 27.9h（15×201、3×400） | **dead from trans（27.9h 窗口）/ 月底批次 unknown**——trans v1 的呼叫點在 `createPatientBatch`（批次端點） |
| `POST /api/patient/create-patient` | 0 | 0 | **無任何人**（Prod 0、Staging 0、APM 7d 0） | **dead（全面）** |
| `GET /api/user/login_via_session` | 0 | 0 | **無任何人**（Prod 0、Staging 0、APM 7d 0） | **dead（全面）**；但 trans v1 仍有 code path 讀 `LOG_IN_VIA_SESSION`（見 §6） |

建議遷移順序：**list-customer-by-id（v1 → v2）→ createPatientBatch 內兩條 create-patient → 移除 `GET /login` / `LOG_IN_VIA_SESSION`**。同時要通知 `lis-order` owner：它才是 core v1 HTTP 的最大客戶，VP-18156 的真正 blocker 是 lis-order，不是 trans。

---

## 1. 方法

### 1.1 Datadog Logs（權威計數）

Core v1 每個 HTTP request 產生一筆 winston JSON log，欄位 `method, route, path, status, duration_ms, user_agent, x_forwarded_for, remote_ip, jwt_present, jwt_source, jwt_sub, jwt_role, service_name, environment, ...`。透過內部 MCP server（`analyze_datadog_logs` = DDSQL over 虛擬 `logs` 表；`search_datadog_logs` = 原始 log）查詢。

Logs Explorer 基本 query（可直接貼進 Datadog UI）：

```
@event:core_v1_http_request @environment:Prod
```

注意事項（VP-18140 作者的提醒，實測屬實）：
- **不要用 `env:` / `service:` tag 分 tier**：Prod 與 Staging 兩個 tier 都打 `env:prod`、`service:lis-core-deploymentv7`。要用 `@environment:Prod` / `@environment:Staging`。
- 自訂屬性在 DDSQL 要用 `extra_columns` 宣告成 `@route`、`@user_agent`、`@remote_ip` 等，否則 SQL 看不到。
- 分佈：`@environment:Prod` 58,129 筆、`@environment:Staging` 525 筆（窗口內總數）。

使用的 DDSQL（`extra_columns` 皆為 varchar，`@status`/`@duration_ms` 為 bigint，`@jwt_present` 為 boolean）：

```sql
-- Q1 每條 route 總量
SELECT "@method", "@route", count(*) FROM logs GROUP BY "@method", "@route" ORDER BY count(*) DESC;

-- Q2 呼叫者歸因
SELECT "@route", "@user_agent", "@remote_ip", "@x_forwarded_for", count(*)
FROM logs GROUP BY "@route", "@user_agent", "@remote_ip", "@x_forwarded_for" ORDER BY count(*) DESC LIMIT 300;

-- Q3 目標 route 細分（filter 加上
--   (@route:"/api/clinic/list-customer-by-id/:clinic_id" OR @route:*create-patient* OR @route:*login_via_session*)）
SELECT "@route", "@user_agent", "@remote_ip", "@jwt_present", "@jwt_role", "@status", count(*),
       min(timestamp), max(timestamp), avg("@duration_ms"), max("@duration_ms")
FROM logs GROUP BY 1,2,3,4,5,6 ORDER BY count(*) DESC;

-- Q4 每小時量
SELECT DATE_TRUNC('hour', timestamp), "@route", "@user_agent", count(*)
FROM logs GROUP BY DATE_TRUNC('hour', timestamp), "@route", "@user_agent";

-- Q9 route × 呼叫者類別
SELECT "@method", "@route",
       CASE WHEN "@user_agent" LIKE 'Mozilla%' THEN 'browser'
            WHEN "@user_agent" LIKE 'axios%' AND "@remote_ip" LIKE '::ffff:10.224.%' THEN 'axios-in-cluster'
            ELSE "@user_agent" END AS caller,
       "@jwt_role", count(*), count(DISTINCT "@remote_ip")
FROM logs GROUP BY 1,2,3,4 ORDER BY "@route", count(*) DESC;

-- Q10 trans 型態（叢集內 axios）每日量
-- filter: @event:core_v1_http_request @environment:Prod @user_agent:axios* @remote_ip:\:\:ffff\:10.224.*
SELECT DATE_TRUNC('day', timestamp), "@route", "@user_agent", count(*), count(DISTINCT "@remote_ip")
FROM logs GROUP BY 1,2,3;
```

### 1.2 Datadog APM（呼叫端交叉驗證、延遲）

Traces Explorer query（7 天：now-7d → 2026-09-11T23:15Z）：

```
# trans → core v1 HTTP 的 outbound client span
service:(lis-trans-deployment OR lis-transv2-deployment) operation_name:http.request
  (@http.url:*lis-core-http-service* OR @peer.hostname:lis-core-http-service*)

# 誰在打 list-customer-by-id（排除 core 自己與 lis-order）
@http.url:*list-customer-by-id* -service:(lis-core-deploymentv7 OR lis-order)

# create-patient / login_via_session 的非 core、非 order 呼叫者
@http.url:*create-patient* -service:(lis-core-deploymentv7 OR lis-order)
@http.url:*login_via_session*
```

APM 沒有 aggregate 工具，計數與 p95 是把 span 全數分頁抓回（289 筆）後本地計算。**APM 是抽樣資料**（`retainedby: diversity_sampling`），只能當下限與延遲來源；計數以 Logs 為準（見 §5 caveat）。

### 1.3 歸因鏈（沒有 service-name header 的情況下怎麼確定是 trans）

1. Log 端：`user_agent = axios/<ver>`、`remote_ip = ::ffff:10.224.x.x`（AKS pod CIDR，叢集內直連 `lis-core-http-service:30112`，無 Cloudflare 前置，`x_forwarded_for` 為空）、`jwt_present=false`（trans 打 `list_customer_by_id_carlos` 時不帶 token，與 code 一致）。
2. axios 版本對 repo lock file：`LIS-transformer/package-lock.json` → axios **1.13.6**；`LIS-transformer-v2/package-lock.json` → axios **1.16.0**。Log 上正好只有這兩個叢集內 axios 版本。（lock 取自本機 `feature/leo/TRANS-OPT` branch，與 prod image 未逐一比對，屬佐證非證明。）
3. APM 端：`lis-trans-deployment` 與 `lis-transv2-deployment` 都有 `http.request` client span，`http.url = http://lis-core-http-service.default.svc.cluster.local:30112/api/clinic/list-customer-by-id/<id>`、`peer.service = lis-core-deploymentv7`。
4. Log 的 `trace_id` 反查 trace：axios/1.16.0 樣本 `6aa47b0500000000782bd97310eacb0c` 的 root span 為 `lis-transv2-deployment POST /setting/setPracticeInfoClinic`（ https://us3.datadoghq.com/apm/trace/6aa47b0500000000782bd97310eacb0c ）。

四條證據互相一致 → axios/1.13.6 = trans v1、axios/1.16.0 = trans v2。

---

## 2. Prod 全貌（27.9h，n = 58,110）

| method | route | n | 主要呼叫者 |
|---|---|---:|---|
| GET | `/api/patient/get-patient-by-id` | 33,773 | lis-order（兩個 UA）100% |
| GET | `/api/clinic/list-customer-by-id/:clinic_id` | 9,489 | lis-order 95%、trans v1 4.7%、trans v2 0.2% |
| GET | `/api/customer/find-customer` | 8,137 | lis-order 100% |
| GET | `/api/customer/policy-acceptances` | 4,268 | browser（jwt_role clinic/customer） |
| GET | `/api/patient/fuzzy-search-clinic-patients-by-name` | 1,068 | lis-order 100% |
| POST | `/api/user/lis_log_in` | 560 | browser 549、外部 axios/1.16.0 11 |
| POST | `/api/user/multi_login_test` | 534 | lis-order 100% |
| PUT | `/api/patient/update-patient-with-write-back` | 202 | 外部 axios/1.15.2 131 + axios/1.4.0 68（jwt_role `it`）、lis-order 3 |
| POST | `/api/customer/customer-accept-policy` | 56 | browser |
| POST | `/api/patient/create-patient-new` | 18 | lis-order 100% |
| GET | `/api/patient/merge-patients` | 3 | browser（support） |
| POST | `/api/customer/merge-selected-samples-between-customers` | 2 | 外部 axios/1.4.0（support） |
| POST | `/api/patient/create-patient` | **0** | — |
| GET | `/api/user/login_via_session` | **0** | — |

Route 共 12 條有流量。lis-order 一家就佔約 53,000 / 58,110（91%）。

關於 lis-order 的兩個 UA：`Java/1.8.0_202`（JDK 預設）與 `vibrant/order-service-spring`。Datadog change-tracking 顯示 `lis-order` 於 **2026-09-10 20:59:35Z** 部署新版（`3523bec…`，前版 `768969f…`），`vibrant/order-service-spring` UA 第一筆為 20:59:58Z，時間吻合；但 `Java/1.8.0_202` 之後仍持續高量。Java UA 樣本 trace `6aa48bab00000000353db274b1bd782d` root 亦為 `lis-order`（`GET /customer/getJwtTokenCustomerList` → `GET /v1/lis/lis-core-service/api/clinic/list-customer-by-id/?` → core）。推論：lis-order 內有兩套 HTTP client，只有一套帶自訂 UA。兩者都走公網 gateway `api.vibrant-wellness.com/v1/lis/lis-core-service/...`，故 `remote_ip` 全是 Cloudflare IP（104.22.x / 162.158.x / 172.x），無法用 IP 分辨。

---

## 3. 目標 route 逐條

### 3.1 `GET /api/clinic/list-customer-by-id/:clinic_id`（trans env key `list_customer_by_id_carlos`）

Prod 27.9h，n = 9,489（Q3 快照；Q9 稍晚快照為 9,504），status 全部 200。

| 呼叫者 | UA | 來源 IP | JWT | n | 每小時峰值 | avg / max ms |
|---|---|---|---|---:|---:|---|
| lis-order | `vibrant/order-service-spring` | Cloudflare（20 IP） | admin | 4,694 | 568 | ~225 / 1,385 |
| lis-order | `Java/1.8.0_202` | Cloudflare（75 IP） | admin | 4,331 | 646 | ~228 / 4,570 |
| **trans v1** | `axios/1.13.6` | `::ffff:10.224.x.x`（14 個 pod IP） | none | **448** | 80（09-11 10:00Z） | ~205 / 661 |
| **trans v2** | `axios/1.16.0` | `::ffff:10.224.x.x`（5 個 pod IP） | none | **19** | 3 | ~215 / 286 |
| 一次性 | `python-httpx/0.28.1` | Cloudflare | INTERNAL | 1（09-10 19:57:48Z） | — | 239 |

trans 每日量（Q10）：

| 日期（UTC） | trans v1 `axios/1.13.6` | trans v2 `axios/1.16.0` |
|---|---:|---:|
| 2026-09-10（僅 19:22Z 起，4.6h） | 59 | 6 |
| 2026-09-11（整天） | **389** | **13** |

trans v1 的 pod IP 在 09-11 17:3x Z 整批換了一組（`10.224.1.22 / 1.179 / 0.170` → `10.224.0.16 / 2.123 / 0.43 …`），符合一次 rollout；不影響計數。

APM 交叉驗證（7d，抽樣後）：

| service | spans (7d) | p50 | p95 | max | 每日 spans（09-04 → 09-11） |
|---|---:|---:|---:|---:|---|
| `lis-trans-deployment` | 252 | 243 ms | **302 ms** | 1,680 ms | 2 / 45 / 20 / 13 / 34 / 49 / 40 / 49 |
| `lis-transv2-deployment` | 37 | 241 ms | **296 ms** | 3,680 ms | – / 6 / 2 / 2 / 6 / 6 / 8 / 7 |

09-11 log 端 trans v1 為 389、APM 為 49 → APM 保留率約 1/8；APM 每日 spans 在 09-04 → 09-11 都有，代表 **7 天內每天都有 trans → core v1 HTTP 流量**，不是 log 上線那兩天的偶發。

每次呼叫穩定 ~200–300 ms（p95），是 trans 這條路徑上明顯可省的一段（gRPC `lis.ClinicService/ListClinicCustomersByClinicID` 已在 trans v1 的其他 span 看到在用，見 §7）。

**判定：live from trans v1 與 trans v2。** 但即使 trans 全部遷走，此 route 仍有 lis-order 約 9,000 / 天，route 不能刪。

### 3.2 `POST /api/patient/create-patient-new`（trans env key `create_patientv2`，帶 Bearer）

Prod 27.9h：18 筆（15×201、3×400），全部 `Java/1.8.0_202` + admin JWT + Cloudflare IP，10 個 IP，分散在每小時 1–3 筆。APM 7d：`lis-order POST /v1/lis/lis-core-service/api/patient/create-patient-new` 4 spans；非 core 非 order 的 create-patient span 0。

trans 端：0 筆叢集內 axios、0 筆 Bearer 且無 JWT role 的呼叫。trans v1 的呼叫點在 `src/utility/utility.service.ts:8345`，包在 **`createPatientBatch`**（`utility.service.ts:8057`，由 `utility.controller.ts:1497` 的 `@Post('/createPatientBatch')` 端點觸發）——是批次匯入路徑，27.9h 沒看到不代表月底不會有。trans v2 沒有對 core v1 的 create-patient 呼叫（v2 repo 的 `create-patient.*` 是自家 calendar/migration DTO 與 service，不打 core v1 HTTP）。

**判定：dead from trans（本窗口）/ 批次 unknown。** 非 trans 呼叫者 lis-order 為 live。

### 3.3 `POST /api/patient/create-patient`（trans env key `create_patient`）

Prod 0、Staging 0、APM 7d 0（任何 service）。trans v1 呼叫點 `utility.service.ts:8134`，同樣在 `createPatientBatch` 內（舊版分支）。

**判定：dead（全面）**，同樣帶「批次 unknown」保留。

### 3.4 `GET /api/user/login_via_session`（env key `LOG_IN_VIA_SESSION`）

Prod 0、Staging 0、APM 7d 0。

**判定：dead（全面）。** 修正一個前提：任務描述說「no code reads it」，實際上 **trans v1 有讀**——`src/utility/utility.service.ts:254` 的 `login(session, request_id)` 用 `env.LOG_IN_VIA_SESSION + session` 打 axios GET，由 `src/utility/utility.controller.ts` 的 `@Get('/login')`（約 line 128）曝露。trans v2 沒有。流量為零，屬可刪的死 code path。

---

## 4. 其他（非 trans）呼叫者清單

決定 route 能不能刪的是這些人，不是 trans：

| 呼叫者 | 識別方式 | 打的 route | 量（27.9h） |
|---|---|---|---|
| **`lis-order`**（Java/Spring，公網 gateway 進來） | UA `Java/1.8.0_202` + `vibrant/order-service-spring`、APM service `lis-order`、trace root | get-patient-by-id、find-customer、**list-customer-by-id**、fuzzy-search-clinic-patients-by-name、multi_login_test、**create-patient-new**、update-patient-with-write-back | ≈53,000 |
| Portal 前端（browser） | UA `Mozilla/*`、jwt_role clinic / customer / clinic_admin_addon / support | policy-acceptances、customer-accept-policy、lis_log_in、merge-patients | ≈4,900 |
| 未識別 Node service A | UA `axios/1.15.2` + `axios/1.4.0`、jwt_role `it`、Cloudflare IP（19 IP） | update-patient-with-write-back | 199 |
| 未識別 Node client B | UA `axios/1.16.0`、無 JWT、Cloudflare IP（8 IP） | lis_log_in | 11 |
| 未識別 Node client C | UA `axios/1.4.0`、jwt_role `support` | merge-selected-samples-between-customers | 2 |
| 一次性 script | UA `python-httpx/0.28.1`、jwt_role `INTERNAL` | list-customer-by-id | 1 |

A/B/C 都從 Cloudflare 進來（不是叢集內），與 trans 無關；A 的 `it` role 與 write-back 語意像是 IT 工具或 portal-backend 類的 Node 服務，需另行確認。

Staging（`@environment:Staging`，525 筆）順帶確認：staging 的 trans 也在打 list-customer-by-id（`axios/1.16.0` 19 筆自 `10.224.1.177 / 2.182 / 2.239`，`axios/1.13.6` 6 筆自 `10.224.1.37 / 2.112 / 2.102`），其餘為 `vibrant/order-service-spring` 與 VP-18140 的 `vp18140-probe`。

---

## 5. Caveats

1. **窗口只有 27.9 小時**（log 09-10 19:22Z 才開始）。月底 / 月初批次（特別是 trans v1 `createPatientBatch` 路徑）完全沒被觀測到。create-patient 兩條的「dead」判定必須在 **2026-10-01 之後**（涵蓋 9 月底）重跑 Q3/Q10 才能定案。
2. **`jwt_sub` 全部是空字串**——所有 58k 筆，包括 lis-order 帶 admin JWT 的呼叫，`jwt_sub` 都是 `""`（`count(DISTINCT "@jwt_sub")` 每個 UA 都是 1，且值為空）。此欄位目前對歸因無用；可能 middleware 讀的 claim 名稱與實際 token 不同（例如 token 用 `id` / `user_id` 而非 `sub`）。建議回饋到 VP-18140。本報告因此不含任何 jwt_sub 值，也沒有 PHI 風險。
3. **`service_name` 恆為 `unknown`**（呼叫端沒送 header），歸因只能靠 UA + IP + APM。
4. **kubectl 不可用**：本機 `kubectl` 因 Azure MFA 過期失敗（`AADSTS50078`，需互動式 `az login`，未代做）。pod IP → deployment 的直接對照沒做；改用 §1.3 的四條證據鏈替代，結論不受影響。
5. **APM 是抽樣**（`diversity_sampling`），保留率約 1/8；APM 的 count 是下限，p95 是抽樣後的估計。計數以 Logs 為準。
6. `Java/1.8.0_202` 歸給 lis-order 的證據是一筆 trace（另一筆樣本 trace 未被保留）。無法排除還有其他未裝 APM 的 Java 服務也用預設 UA；但就本報告目的（trans 是否 live）無影響。
7. axios 版本 ↔ repo 的對照取自本機 `feature/leo/TRANS-OPT` branch 的 lock file，未對 prod image 逐一驗證。
8. Log 的 `count` 在查詢期間持續增加（Q1 = 58,110、Q6 = 58,129、Q9 略高），各表數字之間有個位數到十位數的時差差異，屬正常。

---

## 6. 每條 route 的判定與建議順序

| 順序 | Route | 判定 | 動作 |
|---|---|---|---|
| 1 | `GET /api/clinic/list-customer-by-id/:clinic_id` | **live from trans v1（~390/天）與 trans v2（~13–19/天）** | 先做。trans v1 `setting.practiceInfo.service.ts:9039`、trans v2 `setting.service.ts:1565` 改走 gRPC `lis.ClinicService/ListClinicCustomersByClinicID`（trans v1 APM 已見此 gRPC 在用，client 現成）。驗收：Q10 的 `axios-in-cluster` 計數歸零。每次省 ~250–300 ms p95。 |
| 2 | `POST /api/patient/create-patient-new` | **dead from trans（27.9h）/ 批次 unknown**；lis-order live | 在 `createPatientBatch` 內改走 core v2 gRPC 等價方法；因目前看不到流量，改完只能靠 staging 觸發批次驗證，並在 10-01 後重跑本報告 Q3 確認 prod 從未再出現 Bearer + 叢集內 IP 的呼叫。 |
| 3 | `POST /api/patient/create-patient` | **dead（全面）** | 與 2 一起處理；舊版分支（`utility.service.ts:8134`）可直接移除或併入同一 gRPC 呼叫。 |
| 4 | `GET /api/user/login_via_session` | **dead（全面）**，但 trans v1 有 `GET /login` code path | 刪 `utility.controller.ts` 的 `@Get('/login')` + `utility.service.ts:254` 的 `login()` + env `LOG_IN_VIA_SESSION`。零流量，風險最低，但也最沒有速度收益，排最後。 |

跨團隊：**VP-18156 要能在 2026-10-31 刪掉整個 core v1 HTTP surface，關鍵在 lis-order**（get-patient-by-id 33k、find-customer 8k、list-customer-by-id 9k、fuzzy-search 1k、multi_login_test 0.5k、create-patient-new、update-patient-with-write-back），以及 portal 前端的 policy-acceptances / customer-accept-policy / lis_log_in / merge-patients，和三個未識別的外部 Node client。這些都不在 trans 專案範圍，建議把 §2、§4 的表轉給 VP-18156 owner。

---

## 7. 順帶觀察

- trans v1 對 core 的 gRPC 呼叫（`lis-core-grpc-service:30113`，`lis.CustomerService/GetCustomer`、`lis.ClinicService/ListClinicCustomersByClinicID`、`lis.SettingService/GetSettingByCustomerClinic`）在 APM 上量很大（7d `http.request` spans 308k），表示 gRPC client 與 `ListClinicCustomersByClinicID` 方法本身已在 prod 跑；順序 1 的遷移不需要新 proto。
- trans v1 在 APM 也有 `GET /setting/list-customer-by-id/:clinic_id` 的 **inbound** span（`api.vibrant-wellness.com/setting/list-customer-by-id/<id>`），即 trans 自己對外提供的同名 wrapper 端點；core v1 呼叫是它的下游。遷移時前端合約不變。
- Staging tier 的 core log 與 Prod 混在同一個 `service` / `env` tag 下，任何 Datadog monitor 若以 `service:lis-core-deploymentv7` 建，會把兩 tier 加總；要用 `@environment`。
