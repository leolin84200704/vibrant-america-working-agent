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
- 18:40 → 20:20 UTC（約 100 分鐘）：`DEADLINE_EXCEEDED` **0 筆**、coresamples error span **0 筆**、pod restarts **0**。**通過。**

### trans v2（歸因乾淨，只有我的三個 PR）
| 指標 | 09-15 同時段 | 09-16 改後 |
|---|---|---|
| `post_/graphql` p95 | 1.106 s | 1.094 s |

如預期持平——#626 純註解、#637 只在 hang 時才作用。

### trans v1（**歸因不成立**）
19:00–20:15 UTC vs 09-15 同時段。live image 是 `402d78e`，含 #781 #782（我，no-op）+ #783 + #784（他人）。

| 端點 | 09-15 p50 | 09-16 p50 | 09-15 p95 | 09-16 p95 |
|---|---|---|---|---|
| findPatient | 0.874 | 0.834 | 1.186 | 1.054 |
| createPatient | 3.138 | 2.036 | 4.365 | 2.036 |
| getTimeLine | 1.839 | 1.836 | 1.844 | 1.837 |
| newrange | 1.800 | 1.952 | 1.809 | 1.971 |
| getSetting | 0.192 | 0.195 | 0.341 | 0.374 |

流量相當（findPatient 1258 → 1209、getSetting 8785 → 8550），比較公平。改善屬於 #783 / #784，不屬於本次。

## 19:00–20:20 的錯誤突波：查證後**不是回歸**

一度看起來像回歸，逐項查完不成立。過程與更正記錄如下，避免下次重跑：

- **看起來的訊號**：getTimeLine 在 12:00–18:44 是 0 錯誤（含只有我的 image 在線的 18:32–18:44，91 個請求 0 錯誤），18:50–20:20 變成 30/716 = 4.2%；ifconfirmaddressv2 0/60 → 10/492；listsamplesaccesionid 1/30 → 31/232。
- **排除 #784**：它的 diff 只落在 trans.service.ts 的 reference-range 區段（5217-5512 等），**沒有碰 `listSamplesAccesionID` 或 `getTimeLine`**。時間相關但機制對不上。
- **排除 on-prem ECONNREFUSED**：`192.168.60.6` 連線被拒是長期問題，09-15 每小時 10~31 筆，今天反而更少。
- **我自己的錯誤判斷（更正）**：我一度說 `trans-patient-info.controller.ts:1247` 的 TypeError 是「全新」——**錯的**。拉 09-10 以來的歷史，它每天都在發生（09-11 一天 46 筆、09-15 25 筆），今天 23 筆屬正常範圍。當時的搜尋字串沒對上 log 格式，回傳 0 筆被我誤讀成「歷史上沒發生過」。查歷史要用 log 裡真正出現的字串（這裡是檔名:行號），不要用自己拼的描述。
- **結論**：突波在 20:05 後自行消退（15 分鐘內 getTimeLine 1 筆、listsamplesaccesionid 2 筆），與 19:02–20:14 的 on-prem gRPC 波動同時段。判定為下游短暫抖動，非任何一次 deploy 造成。


## 完整窗（19:00–21:00 UTC）+ 第二個對照日 → 更正

只用「9/15 同時段」單一對照日時，newrange 看起來慢 6–8%、getSetting p95 看起來差 17%，我一度建議回報給 #784 作者。**加上 9/14（週一）第二個對照日後兩者都溶解**：

| 端點 | 09-14 對照 | 09-15 對照 | 09-16 改後 |
|---|---|---|---|
| newrange p95 | **2.551 s** | 1.888 s | 2.013 s |
| getSetting p95 | **0.415 s** | 0.347 s | 0.405 s |

09-16 兩者都**落在兩個對照日之間**，不是落在外面——9/15 只是狀況特別好的一天。**都不是回歸。**

**教訓：單一對照日不足以判定這些端點上的個位數百分比變化。** 至少要兩個對照日才能分辨「變差」和「對照日剛好很好」。

完整窗 v1（19:00–21:00 UTC，hits：findPatient 1,910、getSetting 14,431、newrange 1,027）：

| 端點 | 09-15 p50 | 09-16 p50 | 09-15 p95 | 09-16 p95 |
|---|---|---|---|---|
| findPatient | 0.871 | 0.854 | 1.189 | 1.099 |
| createPatient | 2.644 | 2.024 | 3.451 | 2.024 |
| getTimeLine | 1.871 | 1.858 | 1.876 | 1.863 |
| newrange | 1.860 | 1.969 | 1.888 | 2.013 |
| getSetting | 0.192 | 0.195 | 0.347 | 0.405 |

Confluence 2684321795 已更新到 version 3，§5.6 換成三日對照表並寫入這條更正。
