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

## 改後第一批（deploy 02:18 UTC → 量測窗 02:25–03:05 UTC，週一深夜 PT 低流量）

| 端點 | 窗內 hits | 改後 p50 | 改前 7 天 p50 | 前一天同時段 p50 | 我的預估 | 判定 |
|---|---|---|---|---|---|---|
| createPatient | 10 | **1.68 s** | 3.56 s | 3.59 s（n=2） | ~2 s | 符合，比預估更好。一筆 trace：kafka.produce 12 次共 0.70 s、tcp.connect 3 次（改前 14/14）；request 1.89 s，其中 core CreatePatientV2 0.84 s |
| getTimeLine（#774；kit 仍走 HTTP，shadow 中） | 17 | **1.71 s** | 2.15 s | 2.28 s（n=11） | p50 −0.25 s | 符合（−0.44 s，樣本小） |
| newrange | 40 | **2.05 s**（p95 2.10） | 2.06 s（p95 4.69） | 2.96 s（n=11） | p50 小幅、p95 明顯下降 | p50 如預估不動（快取命中的請求不受影響）；p95 樣本太小待白天 |
| findPatient | 113 | **1.10 s**（p95 1.11） | 1.21 s（p95 2.88） | — | p95 2.8→~2.1 | 方向對，待工作日尖峰 |

kit shadow（02:21–03:03 UTC，16 筆）：equal 16/16；HTTP 路 p50 ~1.1 s（0.86–1.93 s），內部路 p50 ~0.37 s（7 ms 快取命中到 1.03 s）。切 `inprocess` 後 getTimeLine 預估再省約 0.7–1.2 s，與「p50 2.2 → ~1.0 s」一致。

錯誤：createPatient / getTimeLine 0；newrange 4/40（7 天基線 169/9,435 = 1.8%）。indexed spans 顯示改後 8 筆 500 的 p50 = 78 ms，與改前 327 筆 500 的 p50 78 ms 完全相同 → 是既有的快速失敗類（`'No order found'` / `patient_order` undefined），發生在進到本次改動的函式之前。深夜樣本小，白天再看比率。

注意：Datadog scalar 的 p95 是各時間桶百分位的平均，窗短、樣本少時 p95 會塌到 ≈ p50（上表 newrange / findPatient 皆如此），只能看方向，白天用完整分佈再量。
