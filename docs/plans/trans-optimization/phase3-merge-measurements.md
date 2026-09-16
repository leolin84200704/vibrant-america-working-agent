# 2026-09-16 merge — 前後量測

前置狀態：v1 live `dae5611`、v2 live `254cc28`（= 各自 origin/main），11:05 PDT。
量測窗：**16:00–18:00 UTC（09:00–11:00 PDT）工作日**，merge 前最後一個完整窗。

## 改前基線（2026-09-16 16:00–18:00 UTC）

### trans v1 `trace.express.request`
| 端點 | p50 | p95 |
|---|---|---|
| `post_/trans/findpatient` | 0.873 s | 1.155 s |
| `post_/utility/createpatient` | 1.668 s | 1.668 s |
| `post_/trans/gettimeline` | 1.767 s | 1.781 s |
| `get_/trans/patienttestresultnewrange` | 1.709 s | 1.799 s |
| `get_/utility/getsetting` | 0.193 s | 0.328 s |

### trans v2 `trace.express.request`
| 端點 | p50 | p95 |
|---|---|---|
| `post_/graphql` | 0.269 s | 1.287 s |

### trans v2 → coresamples gRPC（`trace.grpc.client`，#634 的目標面）
| rpc | p50 | 2 小時 hits |
|---|---|---|
| `rbacservice/checkpermission` | 0.0090 s | 50 |
| `rbacservice/getrolepermissions` | 0.0099 s | 35 |
| `settingservice/getclinicsetting` | 0.0272 s | 37 |
| `orderservice/gettransactionhistory` | 0.1474 s | 1 |

**流量極低（2 小時 ~123 次）→ #634 的延遲影響在這個量級下量不出來。**

## #634 前提查證（2026-09-16，Datadog 恢復後補做）

- `service:lis-transv2-deployment env:prod` 近 **7 天** 搜尋 `ENHANCE_YOUR_CALM` / `GOAWAY` / `too_many_pings` / `excess pings` → **0 筆**。
- 同期 `/coresamples_service.*` 的 error span 共 **1 筆**（2026-09-09 18:20Z），內容是
  `14 UNAVAILABLE: No connection established. Last error: connect ECONNREFUSED 10.0.69.10:8084`
  —— 連線被拒，不是 keepalive ping 被伺服器拒絕。

**結論：#634 的假設（v2 正在被 server 以 keepalive 政策拆通道）證偽。**

## Deploy pipeline 時間（CI gate 的成本）

改前（無 gate）成功 run：
- v1：10m49s / 10m39s / 11m36s / 10m34s（平均 ~10.9 min）
- v2：8m52s / 9m32s / 9m53s / 8m59s（平均 ~9.3 min）

改後：見下方「改後」段落。

## Merge / deploy 時間軸（UTC，2026-09-16）

| 時間 | 上線 | repo | runtime 影響 |
|---|---|---|---|
| 16:00–18:00 | — | — | **基線窗** |
| 18:20 | `796e2c4` PR #781 CI gate | v1 | 無 |
| 18:29 | `dae8a09` **PR #783（YFvibrant）getTnpCode memoize** | v1 | **有，直打 findPatient** |
| 18:32 | `20702b7` PR #782 刪 dead code | v1 | 無 |
| 18:30 | `a8d2ae9` PR #626 純註解 | v2 | 無 |
| 18:40 | `3855769` PR #637 coresamples 60 s deadline | v2 | 有（只在 hang 時） |

Live 核對：v1 3 pods = `20702b7`、v2 3 pods = `3855769`，兩邊都等於各自 origin/main。併發 deploy（v2 有兩個 run）沒有出現舊 image 覆蓋新 image。Pod restarts 全 0。

**歸因警告**：PR #783 由別人在 18:14 merge、18:29 上線，落在量測窗內且直接針對 findPatient。
**18:29 之後 v1 的任何延遲改善都屬於 #783，不屬於本次的 #781 / #782（兩者皆 runtime no-op）。**
v2 側乾淨：`254cc28` 之後只有 #633 / #626 / #637 三個，全部是我的。

## Deploy pipeline 時間（CI gate 成本）

| repo | 改前平均 | 改後 | gate job |
|---|---|---|---|
| v1 | ~10.9 min | 14.0 min | 2m47s |
| v2 | ~9.3 min | 12.6 min | 2m47s |

gate 在 deploy pipeline 的第一次實戰即通過（兩 repo）。

## 改後量測
（19:00–21:00 UTC = 12:00–14:00 PDT；另取 2026-09-15 同時段當 time-of-day 對照）

### #637 驗收（deadline，不看延遲看有無誤砍）
- 18:40–18:43 UTC：`DEADLINE_EXCEEDED` **0 筆**；pod restarts 0。
- 完整窗結果：待填。
