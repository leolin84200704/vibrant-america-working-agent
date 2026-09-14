# Phase 0.1 — trans v1 / v2 最慢端點清單（Datadog APM 實測）

> 產出日期：2026-09-11（資料擷取時間 2026-09-11 22:40–23:25 UTC）
> 資料來源：Datadog APM（org `us3.datadoghq.com`），經內部 Vibrant MCP Server（`analyze_datadog_logs` 的 DDSQL、`search_datadog_spans`、`get_datadog_trace`）
> 對應 PLAN.md Phase 0.1；只讀不改，未動任何 repo / Jira / config。

## 0. 摘要（先講結論）

| 項目 | 結果 |
|---|---|
| Datadog service 名 | v1 = `lis-trans-deployment`、v2 = `lis-transv2-deployment`，皆 `env:prod`（`-st` 後綴是 staging 部署，另一個 service 名，已排除） |
| 7 天總量 | v1 REST 1,445,633 hits（144 個 resource；扣掉 `OPTIONS` / `GET /health` 後 822,628）；v1 gRPC server 22,862；v2 REST 593,633（扣 `GET /health` / `OPTIONS` 後 128,000，其中 `POST /graphql` 119,413）；v2 GraphQL operation 119,430（76 個 operation） |
| p95 > 2 s 且 7d ≥ 100 hits 的端點 | **11 個**（v1 REST 9、v1 gRPC 1、v2 GraphQL 1）；不設 hits 門檻則 27 個 —— 與會議「10–20 支」的印象一致 |
| 使用者痛點 Top-5（p95 × hits） | `GET /dashboard/user/timeline`、`GET /utility/getSetting`、`POST /trans/findPatient`、`GET /proxy/old-report/downloadTestOrderPDF`、`GET /trans/patientTestResultnewrange`（v2 整體 `POST /graphql` 若算一支會排第 1，但它是所有 operation 的總和） |
| 最大意外 | **高峰時段（週間 08–12 PDT）的 p95 與全週 p95 幾乎相同**（痛點 Top-10 全在 ±5% 內；Top-20 最大偏差 -22% / +41%，且沒有一致變慢的方向）。慢不是流量擠出來的，是每支端點結構性的下游 fan-out（對 core 的 N+1 gRPC、公網回繞 `api.vibrant-wellness.com`、自己打自己的 HTTP）。Phase 2 的並行化 / 去重方向是對的，但「peak 才慢」的前提要修正 |
| 第二個意外 | `GET /utility/getSetting` 單支 7 天 310k 次（占 v1 有效流量 38%），p95 只有 333 ms，但 p99 1.8 s，且每次要打 9 支 core gRPC；其他慢端點（PDF、getTimeLine）內部又會經 HTTP 再打一次 getSetting。它是全系統的放大器 |

## 1. 方法與重現方式

### 1.1 為什麼用 metrics 而不是 spans

`search_datadog_spans` 拿到的是 **indexed spans**，每一筆都帶 `retainedby: diversity_sampling` 或 `retention_filter`（後者專留 error / 高延遲），7 天 v1 REST 只有約 25k 筆被 index，對比實際 1.45M hits 約 2%，而且刻意偏向慢的請求。用這批算百分位會嚴重高估。MCP server 也沒有 `aggregate_spans` 工具。

改走 APM **trace metrics**（`trace.<operation>.hits` / `.errors` 與 distribution `trace.<operation>`），這些是 agent 在取樣前就對 100% 請求計算的，等同 Datadog Service Page 上的數字。取得方式是 `analyze_datadog_logs` 的 DDSQL 允許呼叫 `dd.metrics_scalar()` / `dd.metrics_timeseries()` PTF（工具描述沒寫，實測可用；`from` / `to` 參數會綁定 metric 的時間窗，已用 1h vs 7d 的 hits 比例驗證）。

### 1.2 實際用的查詢（可直接貼進 Datadog Metrics Explorer / Notebook）

時間窗：7d = `2026-09-04T23:20Z → 2026-09-11T23:20Z`；peak = `2026-09-11T15:00Z → 19:00Z`（週五 08:00–12:00 America/Los_Angeles）。

| 用途 | metric query |
|---|---|
| v1 REST hits | `sum:trace.express.request.hits{service:lis-trans-deployment,env:prod} by {resource_name}.as_count()` |
| v1 REST errors | `sum:trace.express.request.errors{service:lis-trans-deployment,env:prod} by {resource_name}.as_count()` |
| v1 REST p50/p95/p99 | `p95:trace.express.request{service:lis-trans-deployment,env:prod} by {resource_name}.rollup(604800)`（peak 用 `.rollup(14400)`） |
| v1 gRPC server | 同上，metric 換 `trace.grpc.server` |
| v2 REST | 同上，`service:lis-transv2-deployment` |
| v2 GraphQL operation | metric 換 `trace.graphql.execute`（resource_name = 完整 operation 文字，見 §5 注意事項） |
| 每小時流量曲線 | `sum:trace.express.request.hits{service:lis-trans-deployment,env:prod}.as_count().rollup(sum,3600)` |
| findPatient 逐日 p95 | `p95:trace.express.request{service:lis-trans-deployment,env:prod,resource_name:post_/trans/findpatient}.rollup(86400)` |

DDSQL 包裝形式（在 MCP `analyze_datadog_logs` 的 `sql_query`）：
`SELECT tags, value FROM dd.metrics_scalar('<query>', 'sum' | 'avg') ORDER BY value DESC LIMIT 500`

百分位使用 `.rollup(604800)` 把整個 7 天合成單一 DDSketch 再取分位（不是每小時 p95 的平均；兩者對 `getSetting` 分別是 333 ms vs 449 ms，報告一律用前者）。

### 1.3 Service 發現（結論與依據）

| 步驤 | 查詢 | 結果 |
|---|---|---|
| 以已知 resource 找 service | `search_datadog_spans` query `resource_name:"POST /trans/findPatient"` 24h | 回 `service:lis-trans-deployment env:prod`（tags `kube_deployment:lis-trans-deployment kube_namespace:default container_name:lis-trans`）；另有 `lis-trans-deployment-st`（`aks-userpool`，staging pods，同樣打 `env:prod`） |
| 以 namespace 找 v2 | `kube_namespace:transv2 @_top_level:1` 24h | `service:lis-transv2-deployment`（`kube_deployment:lis-transv2-deployment`）；另有 `lis-transv2-deployment-st` |
| 反向確認沒有別名 | DDSQL `dd.spans` filter `kube_deployment:(lis-trans-deployment OR lis-transv2-deployment) operation_name:(express.request OR graphql.execute OR grpc.server)` 7d GROUP BY service | 只有兩個 service：`lis-trans-deployment` 25,071、`lis-transv2-deployment` 15,567（indexed spans） |

因此所有數字的 filter 定為 **`service:lis-trans-deployment,env:prod`** 與 **`service:lis-transv2-deployment,env:prod`**。用 service 而不用 `kube_deployment`，因為 trace metrics 只有 service / env / resource_name 等主 tag 可 group。

### 1.4 v1 / v2 各自的 span 結構

- v1：入口 `express.request`（REST，resource 形如 `GET /utility/getSetting`）；另有 `grpc.server`（v1 自己也對外提供 `listrans.TransService` 兩支 gRPC）。
- v2：入口 `express.request`，但幾乎全部落在 `POST /graphql`；真正的 operation 在子 span `graphql.execute`，resource_name 是**整段 query 文字**（例 `query PatientProfileSlow($accessionId:String!...){patientProfile(...){...}}`），dd-trace 沒有把它縮成 operation name。本報告以正則取 `<type> <OperationName>` 顯示。`graphql.resolve` 的 metric 只有 1 個 resource（未按 field 拆），無法直接排 resolver。
- 兩邊對 core 的呼叫都是 `grpc.client`（`peer.service:lis-core-deploymentv7`，`rpc.grpc.path:/lis.*Service/*`），dd-trace 同時會產生一層 `http.request POST` 包住 gRPC（HTTP/2），trace 表格內兩者是**同一段時間**，不可相加。

## 2. 排名表（7 天，2026-09-04 → 09-11）

「痛點分數」= p95(秒) × hits。已把 `OPTIONS`（CORS preflight）、`GET /health`（k8s probe）從 A / B 表排除，只留在 C 表。

### 2A. Top-20 使用者痛點（p95 × hits）

| # | service | endpoint | hits/7d | p50 ms | p95 ms | p99 ms | err % | p95×hits (s) | 計畫已知熱點 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | v2 REST | `POST /graphql`（所有 operation 總和） | 119,413 | 203 | 1,568 | 2,656 | 0.00 | 187,200 | — |
| 2 | v1 REST | `GET /dashboard/user/timeline` | 46,845 | 1,568 | 2,915 | 4,295 | 0.01 | 136,538 | 否（新發現） |
| 3 | v1 REST | `GET /utility/getSetting` | 310,636 | 190 | 333 | 1,831 | 0.01 | 103,316 | 否（PLAN §1.5 S3 有提到聚合邏輯重） |
| 4 | v1 REST | `POST /trans/findPatient` | 29,189 | 1,016 | 2,826 | 5,254 | 0.00 | 82,479 | **是** |
| 5 | v1 REST | `GET /proxy/old-report/downloadTestOrderPDF` | 7,284 | 6,629 | 11,230 | 13,738 | 0.01 | 81,802 | 否 |
| 6 | v1 REST | `GET /trans/patientTestResultnewrange` | 7,335 | 2,310 | 6,135 | 9,180 | 1.87 | 44,998 | **是**（內部即 `getDetailRangeInfo*` 的 N+1，見 §4.5） |
| 7 | v1 REST | `GET /utility/getUserInfoV2` | 65,090 | 252 | 468 | 1,948 | 0.01 | 30,448 | 否 |
| 8 | v1 gRPC | `/listrans.TransService/GetSampleInfo` | 9,769 | 185 | 2,915 | 3,678 | 0.00 | 28,473 | 否 |
| 9 | v1 REST | `POST /trans/getTimeLine` | 7,115 | 2,171 | 3,403 | 5,947 | 0.20 | 24,216 | **是** |
| 10 | v2 GraphQL | `query PatientProfileSlow` | 6,993 | 1,496 | 3,101 | 4,641 | 1.07 | 21,686 | **是**（patientProfile） |
| 11 | v1 REST | `GET /trans/patientTestKitInfo` | 24,899 | 365 | 843 | 2,535 | 0.00 | 20,994 | 否（可能含 `getTubeInfo*`） |
| 12 | v1 REST | `GET /setting/getPracticeInfo` | 44,828 | 182 | 313 | 1,363 | 0.01 | 14,013 | 否 |
| 13 | v1 REST | `POST /utility/GetSampleInfo` | 36,804 | 96 | 377 | 1,617 | 0.00 | 13,857 | 否 |
| 14 | v2 GraphQL | `query PatientProfileFast` | 6,989 | 689 | 1,918 | 3,457 | 1.03 | 13,403 | **是**（patientProfile） |
| 15 | v1 REST | `POST /valogin/login` | 15,291 | 521 | 733 | 2,870 | 0.02 | 11,214 | 否 |
| 16 | v1 REST | `GET /hubspot/announcements` | 22,096 | 272 | 498 | 599 | 0.00 | 10,998 | 否 |
| 17 | v2 GraphQL | `query GET_ALL_OTHER_INFO_NEEDED_BY_IDS` | 5,015 | 1,282 | 1,978 | 4,036 | 0.08 | 9,920 | 否 |
| 18 | v1 REST | `GET /trans/GenerateBatchReqOrReportV2` | 680 | 7,164 | 13,738 | 15,313 | 0.00 | 9,342 | 否 |
| 19 | v1 REST | `POST /utility/createPatient` | 2,072 | 3,853 | 4,499 | 7,053 | 0.00 | 9,322 | 否 |
| 20 | v2 GraphQL | `query PatientPNS` | 5,065 | 1,262 | 1,747 | 2,383 | 0.04 | 8,851 | **是**（PNS） |

### 2B. p95 > 2,000 ms 且 hits/7d ≥ 100（共 11 支，依 p95 排）

| # | service | endpoint | hits/7d | p50 ms | p95 ms | p99 ms | err % | p95×hits (s) |
|---|---|---|---|---|---|---|---|---|
| 1 | v1 REST | `GET /trans/GenerateBatchReqOrReportV2` | 680 | 7,164 | 13,738 | 15,313 | 0.00 | 9,342 |
| 2 | v1 REST | `GET /proxy/old-report/downloadTestOrderPDF` | 7,284 | 6,629 | 11,230 | 13,738 | 0.01 | 81,802 |
| 3 | v1 REST | `GET /trans/downloadTestOrderPDF` | 544 | 6,527 | 11,058 | 14,392 | 0.00 | 6,015 |
| 4 | v1 REST | `GET /trans/patientTestResultnewrange` | 7,335 | 2,310 | 6,135 | 9,180 | 1.87 | 44,998 |
| 5 | v1 REST | `POST /utility/createPatient` | 2,072 | 3,853 | 4,499 | 7,053 | 0.00 | 9,322 |
| 6 | v1 REST | `PUT /utility/updatePatient` | 710 | 1,385 | 4,099 | 5,419 | 0.28 | 2,911 |
| 7 | v1 REST | `POST /trans/getTimeLine` | 7,115 | 2,171 | 3,403 | 5,947 | 0.20 | 24,216 |
| 8 | v2 GraphQL | `query PatientProfileSlow` | 6,993 | 1,496 | 3,101 | 4,641 | 1.07 | 21,686 |
| 9 | v1 REST | `GET /dashboard/user/timeline` | 46,845 | 1,568 | 2,915 | 4,295 | 0.01 | 136,538 |
| 10 | v1 gRPC | `/listrans.TransService/GetSampleInfo` | 9,769 | 185 | 2,915 | 3,678 | 0.00 | 28,473 |
| 11 | v1 REST | `POST /trans/findPatient` | 29,189 | 1,016 | 2,826 | 5,254 | 0.00 | 82,479 |

差一點過線（p95 1.7–2.0 s、量不小）：v2 `query GET_ALL_OTHER_INFO_NEEDED_BY_IDS` 1,978、v2 `query PatientProfileFast` 1,918、v2 `query PatientPNS` 1,747。p95 > 2 s 但 hits < 100 的另有 16 支（多為批次 / 報表類，列在附錄）。

### 2C. Top-10 純流量（含 noise）

| # | service | endpoint | hits/7d | p50 ms | p95 ms | p99 ms | 備註 |
|---|---|---|---|---|---|---|---|
| 1 | v2 REST | `GET /health` | 409,910 | 1 | 3 | 6 | k8s probe，noise |
| 2 | v1 REST | `OPTIONS` | 349,341 | 1 | 2 | 3 | CORS preflight，noise |
| 3 | v1 REST | `GET /utility/getSetting` | 310,636 | 190 | 333 | 1,831 | v1 有效流量 38% |
| 4 | v1 REST | `GET /health` | 273,664 | 2 | 5 | 7 | noise |
| 5 | v2 REST | `POST /graphql` | 119,413 | 203 | 1,568 | 2,656 | 所有 v2 operation |
| 6 | v1 REST | `GET /utility/getUserInfoV2` | 65,090 | 252 | 468 | 1,948 | |
| 7 | v2 REST | `OPTIONS` | 55,749 | 1 | 2 | 4 | noise |
| 8 | v1 REST | `GET /dashboard/user/timeline` | 46,845 | 1,568 | 2,915 | 4,295 | |
| 9 | v1 REST | `GET /setting/getPracticeInfo` | 44,828 | 182 | 313 | 1,363 | |
| 10 | v1 REST | `POST /valogin/renewToken` | 41,610 | 10 | 26 | 985 | |

（第 11、12：`POST /utility/GetSampleInfo` 36,804；`POST /trans/findPatient` 29,189。）

log 交叉驗證：v1 應用 log 的 `@request_type:Response` 7 天計數 `GET /utility/getSetting` 317,403、`POST /trans/findPatient` 32,819，與 metric 的 310,636 / 29,189 相差 2–11%，方向一致（log 多算了少量 4xx 提前結束的請求）。

### 2D. 高峰時段（週五 2026-09-11 08:00–12:00 PDT）Top-20 與全週對照

高峰判定：7 天每小時 hits 曲線（`.rollup(sum,3600)`）轉 PDT 後，週間平均 v1 05:00 起爬升、**08:00–15:00 為高原（18–23k req/h）、11:00 最高（23k）**、16:00 後降到 9k 以下；v2 曲線形狀相同（高原 1.4–2.0k/h）。前 5 名時段：Tue 09-08 11:00 (32.7k)、Wed 09-09 11:00 (31.6k)、Thu 09-10 08:00 (31.5k)。

| # | service | endpoint | hits (4h) | p50 ms | p95 ms | p99 ms | err % | 全週 p95 ms | Δ p95 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | v1 REST | `GET /dashboard/user/timeline` | 3,151 | 1,544 | 3,006 | 4,099 | 0.00 | 2,915 | +3% |
| 2 | v1 REST | `POST /trans/findPatient` | 2,346 | 1,016 | 2,782 | 5,254 | 0.00 | 2,826 | -2% |
| 3 | v1 REST | `GET /utility/getSetting` | 20,138 | 190 | 289 | 1,322 | 0.00 | 333 | -13% |
| 4 | v1 REST | `GET /proxy/old-report/downloadTestOrderPDF` | 404 | 6,733 | 11,058 | 13,114 | 0.00 | 11,230 | -2% |
| 5 | v1 REST | `GET /trans/patientTestResultnewrange` | 611 | 2,383 | 6,427 | 9,617 | 1.47 | 6,135 | +5% |
| 6 | v1 REST | `POST /trans/getTimeLine` | 613 | 2,171 | 3,351 | 4,229 | 0.00 | 3,403 | -2% |
| 7 | v1 REST | `GET /utility/getUserInfoV2` | 4,704 | 252 | 420 | 1,802 | 0.02 | 468 | -10% |
| 8 | v2 GraphQL | `query PatientProfileSlow` | 602 | 1,568 | 3,101 | 4,499 | 0.83 | 3,101 | 0% |
| 9 | v1 REST | `GET /trans/patientTestKitInfo` | 1,622 | 348 | 792 | 1,747 | 0.00 | 843 | -6% |
| 10 | v2 GraphQL | `query PatientProfileFast` | 601 | 689 | 1,888 | 3,678 | 0.83 | 1,918 | -2% |
| 11 | v1 REST | `GET /trans/patientOrderInfo` | 667 | 116 | 1,186 | 2,496 | 0.30 | 1,031 | +15% |
| 12 | v1 REST | `POST /valogin/login` | 1,072 | 513 | 711 | 1,978 | 0.00 | 733 | -3% |
| 13 | v1 REST | `POST /utility/GetSampleInfo` | 2,150 | 101 | 354 | 1,978 | 0.00 | 377 | -6% |
| 14 | v1 REST | `GET /setting/getPracticeInfo` | 3,012 | 185 | 244 | 969 | 0.00 | 313 | -22% |
| 15 | v1 REST | `POST /utility/createPatient` | 154 | 3,853 | 4,499 | 5,254 | 0.00 | 4,499 | 0% |
| 16 | v1 REST | `GET /hubspot/announcements` | 1,392 | 272 | 490 | 590 | 0.00 | 498 | -2% |
| 17 | v1 REST | `GET /trans/listPatientByPatientId` | 599 | 388 | 1,132 | 2,274 | 0.00 | 1,115 | +2% |
| 18 | v1 REST | `GET /trans/downloadTestOrderPDF` | 60 | 6,427 | 10,887 | 12,713 | 0.00 | 11,058 | -2% |
| 19 | v1 REST | `GET /utility/ifConfirmAddressV2` | 520 | 648 | 1,204 | 1,747 | 0.77 | 856 | +41% |
| 20 | v2 GraphQL | `query GetQuestionnaireRequirements` | 580 | 468 | 940 | 1,343 | 0.69 | 940 | 0% |

高峰 4 小時 p95 > 2 s 且 ≥ 20 hits：`GET /dashboard/user/timeline`、`POST /trans/findPatient`、`GET /proxy/old-report/downloadTestOrderPDF`、`GET /trans/patientTestResultnewrange`、`POST /trans/getTimeLine`、`query PatientProfileSlow`、`POST /utility/createPatient`、`GET /trans/downloadTestOrderPDF`、`GET /trans/GenerateBatchReqOrReportV2`、`PUT /utility/updatePatient`、`GET /trans/deep-link/resolve/:token`（11 支，與全週名單幾乎重合）。

**結論：痛點 Top-10 的高峰 p95 與全週差在 ±5% 內，Top-20 內只有 `ifConfirmAddressV2`（+41%）、`getPracticeInfo`（-22%）超出 ±15%，且方向不一致；Top-20 名單不變。** 尾延遲不是容量問題，是端點內部結構。

### 2E. 計畫列出的熱點對照

| PLAN 名稱 | 實際 Datadog resource | 7d hits | p95 ms | 狀態 |
|---|---|---|---|---|
| v1 `POST /trans/findPatient` | 同名 | 29,189 | 2,826 | 確認；痛點 #4、>2s 名單 #11。逐日 p95：09-02→09-09 在 3,150–3,621 之間，09-10 3,199、09-11 2,826；p50 從 1,343 降到 1,016。VP-18197 09-10 部署後有下降跡象，但只有 1.5 天樣本，週五流量也較低，下週再確認 |
| v1 `getTimeLine` | `POST /trans/getTimeLine` | 7,115 | 3,403 | 確認；#9 |
| v2 `patientProfile` | `query PatientProfileSlow` + `query PatientProfileFast`（前端已拆成兩段查詢） | 6,993 + 6,989 | 3,101 / 1,918 | 確認；Slow 是 v2 唯一 >2s 的 operation |
| v2 `PNS` | `query PatientPNS` | 5,065 | 1,747 | 確認；未過 2 s 線但 p99 2,383 |
| v1 `getTubeInfo*` | **不是公開端點**，是 service 內部函式；對外最可能對應 `GET /trans/patientTestKitInfo`（24,899 hits，p95 843）與 `POST /utility/GetSampleInfo`（36,804，p95 377） | — | — | 需在 Phase 2 開工時從 code 對回端點 |
| v1 `getDetailRangeInfo*` | 內部函式；trace 證實它就是 `GET /trans/patientTestResultnewrange` 內對 core `GetPatientDetailedReferenceRangeInOut` 的 N+1（一次請求 365 次 gRPC，見 §4.5） | 7,335 | 6,135 | 確認，且是最明確的 N+1 |

## 3. 錯誤率

- v1 REST 7 天 523 個 error / 1.45M（0.04%）。集中在 `GET /trans/patientTestResultnewrange` 137（1.87%）、`GET /portal/bootstrap` 92、其餘零星。
- v2 GraphQL 2,213 error / 119k（1.85%），但 GraphQL 的 error 是 resolver 丟 `GraphQLError` 就算，含業務性錯誤（例如 `getAllRelatedOrdersByPatientId`、`patientGuestLogin` 的預期失敗）。`PatientProfileSlow` / `Fast` 各約 1.0%。
- v1 gRPC server、v2 REST 幾乎無 error。

## 4. 代表性慢 trace 拆解（Top-5 + 兩支計畫熱點）

方法：對每支端點用 `search_datadog_spans` 以 `@duration:[p95 TO p99]` 區間抓一筆近 3 天的 trace，再用 DDSQL `dd.spans(filter => 'trace_id:<id>')` GROUP BY `service, operation_name, resource_name, @peer.service, @peer.hostname` 加總（不受 `get_datadog_trace` 20k token 截斷影響）。`total ms` 是該類 span 的**時間總和**，並行時會大於 wall time；`max ms` 是單筆最長。dd-trace 對 gRPC 會同時產生 `grpc.client` 與外層 `http.request POST`，是同一段時間，表格只列 `grpc.client`。

### 4.1 `GET /dashboard/user/timeline` — trace `6aa47f1b000000004de1528879144fb9`（wall 3,054 ms）

| 子 span | 對象 | n | total ms | max ms |
|---|---|---|---|---|
| `grpc.client /dashboard.DashBoardService/UserTimelineFetch` | `lis-dashboard-prod-rpc-service.default.svc.cluster.local`（10.0.1.179） | 2 | 3,050 | 2,581 |
| `grpc.client /lis.CustomerService/GetCustomer` | core `lis-core-deploymentv7` | 10 | 2,451 | 267 |
| `grpc.client /lis.SampleService/ListSamples` | core | 1 | 181 | 181 |
| `redis.command RPUSH/LRANGE/EXPIRE/SET/GET` | Azure Redis | 34 | ~58 | 5 |

判讀：時間幾乎全部在下游 **lis-dashboard** 的 `UserTimelineFetch`（單次 2.6 s），trans 本身是薄轉發；另外對 core `GetCustomer` 打了 10 次、每次約 245 ms、合計 2.45 s，數字看起來是**串行**（若並行 total 會遠大於 wall 的占比）。trace 內沒有 lis-dashboard 自己的 span（該服務未接 APM 或未傳遞 context），只能看到 client 端等待。

### 4.2 `GET /utility/getSetting` — p95 樣本 `6aa486650000000043c55733fed9e63f`（357 ms）與 p99 樣本 `6aa48649000000003a783eb637a6b9a9`（1,765 ms）

| 子 span（p95 樣本） | 對象 | n | total ms | max ms |
|---|---|---|---|---|
| `grpc.client /lis.CustomerService/GetCustomer` | core → 再轉 `lis-coresamples-v2-deployment` `GetCustomer` 251 + `ListClinicCustomersByClinicID` 166（coresamples 內 `mysql.query Connect` 101） | 1 | 349 | 349 |
| `grpc.client /lis.ClinicService/ListClinicCustomersByClinicID` | core | 1 | 91 | 91 |
| `grpc.client /lis.SettingService/GetSettingByCustomerClinic` | core | 1 | 71 | 71 |
| `grpc.client /lis.AddressService/ShowCustomerAddress` 等其餘 6 支 | core | 6 | ~160 | 45 |
| 合計 core gRPC | | 9 | 669 | |

| 子 span（p99 樣本） | 對象 | n | total ms | max ms |
|---|---|---|---|---|
| 9 支 core gRPC（`GetCustomer` 1,758、`ListClinicCustomersByClinicID` 1,497、`GetSettingByCustomerClinic` 1,487、`ShowClinicAddress` 1,483、`ShowClinicContact` 1,482、`ShowCustomerContact` 1,462、`ShowCustomerAddress` 1,452、`GetClinicSetting` 1,449、`GetClinicByID` 1,449） | core | 9 | 13,494 | 1,758 |
| core 自己往 coresamples 的 3 支 | `lis-coresamples-v2-deployment` | 3 | 341 | 272 |

判讀：getSetting 每次固定對 core 打 **9 支 gRPC、已並行**（p95 樣本 total 669 vs wall 357）。p99 樣本的 9 支**同時**都變成 ~1.45–1.76 s，而 core 自己的下游只花 341 ms —— 延遲不在業務查詢，在 trans→core 這一跳（連線 / HTTP2 stream 排隊 / core event loop 阻塞其中之一）。兩個樣本的呼叫端都不是瀏覽器：p95 是 `lis-ordermanage-deployment`、p99 是 `lis-order`（Java）經公網 `/v1/portal/trans-service/utility/getSetting` 打進來 —— getSetting 有相當比例是**服務對服務**流量。

### 4.3 `POST /trans/findPatient` — trace `6aa46f1100000000154ec6096a758e00`（3,216 ms）

| 子 span | 對象 | n | total ms | max ms |
|---|---|---|---|---|
| `grpc.client /lis.SampleService/GetSampleTests` | core | 2 | 858 | 820 |
| `http.request GET` | **`lis-base-report` 經公網 `api.vibrant-wellness.com:443`** | 1 | 823 | 823 |
| `grpc.client /lis.PatientService/InitialPatientPageHome` | core | 1 | 632 | 632 |
| `grpc.client /lis.SampleService/GetSampleReceiveRecords` | core | 7 | 484 | 88 |
| `grpc.client /issue.IssueService/BatchGetIssuesByObjectIds` | `lis-issue-system-deployment` | 1 | 471 | 471 |
| `http.request POST` | `lis-order.default.svc.cluster.local:4242`（含 dns 122 + tcp 122） | 1 | 244 | 244 |
| `grpc.client /lis.PatientService/ListCustomerPatientsCount` | core | 1 | 241 | 241 |
| `redis.command GET` | Azure Redis | 78 | 231 | 13 |
| `grpc.client /testresult.TestResultGrpcService/GetPatientTestsResult` | 10.0.23.63:6889 | 1 | 208 | 208 |
| `express.request POST /utility/GetSampleInfo` | **trans v1 自己（經 HTTP 再進來一次）** | 1 | 131 | 131 |
| `grpc.client /lis.CustomerService/IsNewCustomer`、`/lis.SettingService/GetSettingByCustomerClinic` | core | 2 | 169 | 119 |
| 合計 core gRPC | | 14 | ~2,384 | |

判讀：一次 findPatient 對 core 14 次 gRPC（`GetSampleReceiveRecords` 7 次 = 每 sample 一次的 N+1）、78 次 Redis GET、1 次公網回繞到 base-report、1 次自己打自己的 HTTP。core 的 span 沒進 trace（同 4.1 的限制）。

### 4.4 `GET /proxy/old-report/downloadTestOrderPDF` — trace `6aa3879400000000707887ccad8b0729`（11,966 ms）

| 子 span | 對象 | n | total ms | max ms |
|---|---|---|---|---|
| `lis-order servlet.request GET /patientPage/generateNormalOrderPdf` | `lis-order`（Java；trans 轉發過去） | 1 | 10,892 | 10,892 |
| └ `lis-order http.request POST /lisapi/v1/lis/pdf-engine/pdf/convertUrlToPdfWithInfo` | `lis-shipping-deployment-staging`（peer.service 帶 `-staging`，需確認是否 prod 打到 staging 的 pdf-engine） | 3 | 14,034 | 6,918 |
| └ `lis-order http.request GET /v1/portal/trans-service/utility/getSetting` → trans `GET /utility/getSetting` | **trans v1 自己**（一次 PDF 內被打 4 次，每次再 9 支 core gRPC → 37 支 core 呼叫，15,746 span-ms） | 4 | 2,746 | 1,697 |
| `http.request GET` | `lis-base-report` | 2 | 411,205（異常） | 400,177 |

判讀：PDF 的 12 s 中 10.9 s 在 `lis-order` 的 `generateNormalOrderPdf`，其中 pdf-engine 轉檔 3 次共 14 s（並行）、又回頭打 trans getSetting 4 次。trans 只是代理，優化點不在 trans。`lis-base-report` 那筆 400 s 的 span 明顯不是本請求的時間（可能是長連線 / stream 被掛到同 trace），列出但不採信。

### 4.5 `GET /trans/patientTestResultnewrange` — trace `6aa46664000000000ea46e14d65eb31d`（6,212 ms）

| 子 span | 對象 | n | total ms | max ms |
|---|---|---|---|---|
| `grpc.client /lis.ReferenceRangeService/GetPatientDetailedReferenceRangeInOut` | core | **365** | 258,514 | 782 |
| `http.request GET` | `lis-base-report` | 2 | 3,785 | 3,754 |
| `grpc.client /issue.IssueService/GetIssues` + `QueryForeignLink` | `lis-issue-system-deployment` | 2 | 466 | 308 |
| `http.request POST` | `lis-order` | 3 | 316 | 145 |
| `grpc.client /lis.PatientService/GetPatient` | core | 1 | 242 | 242 |
| `grpc.client /testresult.TestResultGrpcService/GetPatientTestsResult` | 10.0.23.63 | 1 | 62 | 62 |

判讀：**教科書級 N+1**：一次請求對 core 打 365 次 `GetPatientDetailedReferenceRangeInOut`（每個 test 一次），累計 258 s 的 span 時間靠並行壓成 6 s；這就是 PLAN 說的 `getDetailRangeInfo*`。同時 1.87% 的 error rate 也是 v1 最高。另有 base-report 單次 3.75 s。

### 4.6 `POST /trans/getTimeLine` — trace `6aa3029e000000002f443aceba7beaef`（4,350 ms）

| 子 span | 對象 | n | total ms | max ms |
|---|---|---|---|---|
| `grpc.client /lis.SampleService/ListSamples` | core（core 自己的 `grpc.server ListSamples` 在 trace 內只有 3 筆合計 270 ms） | 1 | 2,531 | 2,531 |
| `http.request GET` | `lis-base-report` | 2 | 1,800 | 1,402 |
| `express.request GET /trans/patientTestKitInfo` | **trans v1 自己** → 內部再打 `lis-sample-deployment GET /patients/v2/kits` 1,371 → accounting `GET /v1/accounting/charge/invoice` ×2 738、shipping `GetTrackingDetails` 340 | 1 | 519 | 519 |
| `lis-core-deploymentv7 grpc.client /auditlog.AuditLogService/RecordAuditLog` | core 內部 | 1 | 1,461 | 1,461 |
| `grpc.client /lis.SampleService/ListSamplesAccesionID` | core | 1 | 345 | 345 |

判讀：最長一段是 `ListSamples` client 端等 2.5 s，但 core server 端該 RPC 只記到 ~100 ms/次 —— 同 4.2 的現象，時間在 trans→core 之間而非 core 業務邏輯，值得在 Phase 2 之前先量 core 端的 gRPC 連線 / event loop 指標。`RecordAuditLog` 1.46 s 若在 core 的關鍵路徑上也會直接拖慢 caller。

### 4.7 v2 `query PatientProfileSlow` — trace `6aa3d85f000000007fa03e6296e5fb96`（express 3,303 ms）

| 子 span | 對象 | n | total ms | max ms |
|---|---|---|---|---|
| `http.request GET` | `lis-shipping-service.shipping.svc.cluster.local:16256`（in-cluster）與 `lis-interactive-report.report.svc.cluster.local` | 4 | 4,167 | 2,213 |
| `graphql.resolve sample_with_questionnaire_report` | resolver | 1 | 2,242 | 2,242 |
| `grpc.client`（`http.request POST` 包裝） | core | 9 | 1,920 | 1,047 |
| `graphql.resolve` 各 scalar field（`total`、`original_price`… 各 1,727） | 這是 dd-trace 把 field resolve 從 execute 開始計時的假象，不可相加 | ~60 | — | 1,727 |

判讀：v2 的時間在 (a) 對 shipping 的 4 次 HTTP、單次可到 2.2 s；(b) `sample_with_questionnaire_report` resolver 2.2 s；(c) 9 支 core gRPC。與 PLAN §2 手法 3（request 內去重）吻合，但最大單筆是 shipping，去重前先確認 4 次是否同 key。

## 5. 資料注意事項（caveats）

1. **百分位來源是 trace metrics（100% 請求）**，不是 indexed spans；但 DDSketch 相對誤差約 ±2%，且分位值會落在 sketch 的 bucket 邊界（表中多處出現相同的 1,747 / 1,978 / 5,254 ms 屬正常量化現象）。
2. `.rollup(604800)` 把 7 天合成單一分位；Datadog UI 預設顯示的是逐時間點 p95 再平均，數字會略高（getSetting 333 vs 449）。重現時請比對方法。
3. **v2 GraphQL 的 resource_name 是整段 query 文字**（含 selection set），metric tag 被截斷至 200 字並小寫化；本報告用 indexed spans 的原文對回大小寫，再以正則取 operation name。前端若改 selection set，Datadog 會把它算成新 resource，歷史曲線會斷 —— 對照 VP-18141 定義指標時要決定用 `graphql.operation.name` 做 tag（需 tracer 設定）。
4. `graphql.resolve` 沒有按 field 拆 metric（單一 resource），resolver 級排名只能靠個別 trace；且 dd-trace 的 resolve span 對 scalar field 的計時包含父層等待，不能加總。
5. **trace 內下游服務的 span 不齊**：lis-dashboard、lis-base-report、testresult、issue-system 等在多數 trace 沒有自己的 server span（未接 APM 或 context 未傳遞），core 只在部分 trace 出現；因此「時間在下游哪裡」只能看 client 端等待時間。
6. 高峰對照只用了**一個** 4 小時窗（週五 08–12 PDT），週五流量比週二至週四低約 20%；結論「p95 不隨高峰變」已在 Top-20 每一支上成立，但若要更穩可再補週二 / 週三同時段。
7. v1 gRPC server 的 hits（`GetPatientPageStatus` 13,093 / 7d）明顯低於應用 log 中 `GRPC Call` 的頻率（單小時就有 ~780 筆 Response log）；dd-trace 對 grpc server 的計數可能不完整，v1 gRPC 兩支的量請以 log 為準再驗。
8. `retention_filter` / `diversity_sampling` 的 indexed spans 只用來找代表性 trace 與對回名稱，**沒有**用來算任何百分位或計數。
9. 所有查詢都排除了 `lis-trans-deployment-st` / `lis-transv2-deployment-st`（staging pods，同樣打 `env:prod` tag —— 這本身值得在 Phase 0.5 順手修，否則 UI 上按 env 篩會混進 staging）。
10. 未包含 PHI；表中的 trace id 是 Datadog 內部識別碼，可直接貼到 `https://us3.datadoghq.com/apm/trace/<trace_id>`。

## 6. 對 PLAN 的影響

1. **「高峰才慢」的前提要改寫**：Top-20 每一支在高峰 4 小時的 p95 與全週差在 ±15%，慢是結構性 fan-out。Phase 0.7 的 k6 壓測仍要做（防回歸），但不必以「重現高峰」為目標；Phase 2 直接對端點結構下手即可。
2. **Phase 2 候選名單調整**（每端點一票、依痛點分數）：
   - 新增第 1 順位 `GET /dashboard/user/timeline`（46,845 hits、p95 2.9 s、痛點分數最高的單一端點）—— 但 2.6 s 在 lis-dashboard 的 `UserTimelineFetch`，trans 側能做的是把 10 次 `GetCustomer` 串行改並行 / batch，主戰場在 dashboard 團隊；需要開一張跨團隊票而不是 trans 的 C 類改動。
   - 新增 `GET /trans/patientTestResultnewrange`：365 次 `GetPatientDetailedReferenceRangeInOut` 是最明確的 N+1，且 error rate 1.87%；PLAN 手法 2（batch API）—— 先查 core 有沒有 batch 版，沒有就要跟 core 團隊要（不擅自改下游）。
   - `GET /utility/getSetting` 不列入 Phase 2 改邏輯（維持 PLAN §1.5「預設保留」），但它是全系統放大器：310k/7d、每次 9 支 core gRPC、又被 PDF / getTimeLine / lis-order 等以 HTTP 回頭呼叫。建議在 Phase 1 加一條：**對 getSetting 的結果做短 TTL cache（手法 4，已有 redis pattern）**，並統計 caller 分布（瀏覽器 vs 服務）。
   - `findPatient`、`getTimeLine`、`PatientProfileSlow`、`PatientPNS` 維持在名單；`findPatient` 要等 VP-18197 一週後的 p95 再決定投入。
   - PDF 三支（`downloadTestOrderPDF` ×2、`GenerateBatchReqOrReportV2`，p95 11–14 s）時間在 lis-order / pdf-engine，trans 只是 proxy，**不列入 trans 的 Phase 2**，改記錄為跨團隊項目；另需確認 `peer.service:lis-shipping-deployment-staging` 是否代表 prod 打到 staging pdf-engine。
3. **Phase 1.3（公網回繞改 in-cluster）有直接證據**：findPatient、newrange、getTimeLine、PDF 的 trace 都出現 `lis-base-report` 經 `api.vibrant-wellness.com:443` 回繞，單次 0.8–3.8 s；base-report 應排第一批。
4. **新增觀察項給 core**：getSetting p99 與 getTimeLine 的 trace 顯示 trans→core 的 client 端等待遠大於 core server 端處理（1.5 s vs 0.3 s；2.5 s vs 0.1 s）。在 Phase 2 動 trans 之前，建議先在 Datadog 對 `lis-core-deploymentv7` 拉 `grpc.server` 的 p95 與 trans 側 `grpc.client` p95 的差值（同一 resource），確認瓶頸是 core 的 event loop / 連線數還是網路。
5. **指標定義（對齊 VP-18141）**：建議固定用 `trace.express.request` / `trace.graphql.execute` 的 `p95` + `hits` by `resource_name`、`env:prod`、排除 `OPTIONS` / `GET /health`；v2 需在 tracer 設定讓 resource 為 operation name（否則前端改 query 文字就會斷線）。
6. **trans 自己打自己**（findPatient → `POST /utility/GetSampleInfo`、getTimeLine → `GET /trans/patientTestKitInfo`，都是經 HTTP 再進 express）是低風險可改的 C 類：改成直接呼叫 service 方法即省一次 HTTP + JWT 驗證 + 一整份 middleware。

## 附錄 A — 全部端點（hits/7d ≥ 100）

### v1 REST（`trace.express.request`，`service:lis-trans-deployment`）— hits/7d ≥ 100 共 61 個，依 p95×hits 排序，此處列前 20

| # | endpoint | hits/7d | p50 ms | p95 ms | p99 ms | err % | peak hits (4h) | peak p95 ms |
|---|---|---|---|---|---|---|---|---|
| 1 | `GET /dashboard/user/timeline` | 46,845 | 1,568 | 2,915 | 4,295 | 0.01 | 3,151 | 3,006 |
| 2 | `GET /utility/getSetting` | 310,636 | 190 | 333 | 1,831 | 0.01 | 20,138 | 289 |
| 3 | `POST /trans/findPatient` | 29,189 | 1,016 | 2,826 | 5,254 | 0.00 | 2,346 | 2,782 |
| 4 | `GET /proxy/old-report/downloadTestOrderPDF` | 7,284 | 6,629 | 11,230 | 13,738 | 0.01 | 404 | 11,058 |
| 5 | `GET /trans/patientTestResultnewrange` | 7,335 | 2,310 | 6,135 | 9,180 | 1.87 | 611 | 6,427 |
| 6 | `GET /utility/getUserInfoV2` | 65,090 | 252 | 468 | 1,948 | 0.01 | 4,704 | 420 |
| 7 | `POST /trans/getTimeLine` | 7,115 | 2,171 | 3,403 | 5,947 | 0.20 | 613 | 3,351 |
| 8 | `GET /trans/patientTestKitInfo` | 24,899 | 365 | 843 | 2,535 | 0.00 | 1,622 | 792 |
| 9 | `GET /setting/getPracticeInfo` | 44,828 | 182 | 313 | 1,363 | 0.01 | 3,012 | 244 |
| 10 | `POST /utility/GetSampleInfo` | 36,804 | 96 | 377 | 1,617 | 0.00 | 2,150 | 354 |
| 11 | `POST /valogin/login` | 15,291 | 521 | 733 | 2,870 | 0.02 | 1,072 | 711 |
| 12 | `GET /hubspot/announcements` | 22,096 | 272 | 498 | 599 | 0.00 | 1,392 | 490 |
| 13 | `GET /trans/GenerateBatchReqOrReportV2` | 680 | 7,164 | 13,738 | 15,313 | 0.00 | 40 | 13,114 |
| 14 | `POST /utility/createPatient` | 2,072 | 3,853 | 4,499 | 7,053 | 0.00 | 154 | 4,499 |
| 15 | `GET /trans/patientOrderInfo` | 8,308 | 120 | 1,031 | 2,274 | 0.93 | 667 | 1,186 |
| 16 | `GET /trans/listPatientByPatientId` | 6,807 | 413 | 1,115 | 2,420 | 0.12 | 599 | 1,132 |
| 17 | `GET /utility/ifConfirmAddressV2` | 8,364 | 581 | 856 | 1,694 | 0.31 | 520 | 1,204 |
| 18 | `GET /trans/downloadTestOrderPDF` | 544 | 6,527 | 11,058 | 14,392 | 0.00 | 60 | 10,887 |
| 19 | `GET /portal/bootstrap` | 14,267 | 146 | 401 | 911 | 0.64 | 1,015 | 401 |
| 20 | `GET /proxy/grpc/getKitStatus` | 13,467 | 206 | 401 | 1,115 | 0.00 | 1,175 | 359 |

完整四張表（v1 REST 61、v1 gRPC 2、v2 REST 13、v2 GraphQL 36 列）放在同目錄 `phase0-top20-endpoints-appendix.md`。

## 附錄 B — 原始資料與腳本

- 原始 MCP 回應（JSON / SSE）與整理後 TSV 存於本機 scratch：`/private/tmp/claude-502/-Users-hung-l-src-vibrant-america-working-agent/d9cd31cf-6dd8-4ead-a47d-be1496fe26e6/scratchpad/dd/`（`*_7d.tsv`、`*_pk.tsv`、`tsql_*.tsv`、`trace_*.json`、`rows.json`；session 結束後不保證保留，需要長期保存請搬進 repo `docs/plans/trans-optimization/raw/`，其中不含 PHI，但 `trace_*.json` 內有 http.url 的 query string，搬移前先過濾）。
- 呼叫方式：JSON-RPC over Streamable HTTP 到 `http://192.168.60.8:8800/mcp`，`initialize` → `notifications/initialized` → `tools/call`；token 取自 `.env` 的 `VIBRANT_MCP_TOKEN`，未寫入任何檔案。
- 本 session 中 Claude Code 內建的 `mcp__vibrant__*` 工具因 OAuth Dynamic Client Registration 404 無法連線，故全程改用 curl；不影響資料。
