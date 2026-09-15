# Phase 2 — 預估 vs 實測（prod，Datadog trace metrics 100% 請求）

方法：`get_datadog_metric` 對 `trace.express.request` 取 `p50` / `p95`（scalar，`avg` 聚合的是各時間桶的百分位，屬近似）、`.hits` 計數；service `lis-trans-deployment`、`env:prod`、`resource_name` 小寫底線化。改前窗：deploy 前 7 天。改後窗：deploy 完成後起算，並另取「工作日 9–17 PT」對照，避免時段偏差。任何預估與實測的差異，連同原因，回寫到 `project-agent-factory/framework/ENGINEERING-LESSONS.md`。

## 改前基線（2026-09-08 02:10 → 2026-09-15 02:10 UTC）

| 端點 | 7 天 hits | p50 | p95 | PR | 我的預估 |
|---|---|---|---|---|---|
| `POST /trans/findPatient` | 37,715（至 09-14 23:37） | 1.21 s | 2.88 s | #769（09-14 23:38 UTC 上線） | p95 2.8 → ~2.1 s；p50 −0.6 s 級 |
| `POST /utility/createPatient` | 2,661 | 3.56 s | 4.12 s | #773 | p50 ~3.8 → ~2 s（省 ~2.9 s 中的大部分） |
| `POST /trans/getTimeLine` | 9,039 | 2.15 s | 3.22 s | #774（排程）+ #776（kit 改內部，先 shadow） | #774：p50 −0.25 s、p95 −0.5 s；#776 切 inprocess 後 p50 → ~1.0 s、p95 → ~1.6 s |
| `GET /trans/patientTestResultnewrange` | 9,409 | 2.06 s | 4.69 s | #775 | 快取未命中的請求短約 1.5 s（fan-out 長度）；p95 應明顯下降，p50 小幅 |

## 改後（待填）

- findPatient 首批（09-14 23:41–00:28 UTC，191 req，週一傍晚）：p50 0.92 s、p95 0.94 s、錯誤 0。同日改前 20:00–23:37：p50 1.00 / p95 1.55（1,511 req）。**尚不足以下結論**，待工作日。
