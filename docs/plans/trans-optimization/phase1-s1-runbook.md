# Phase 1.1 — S1 runbook：transv2 `checkIfPersonalizedReportCanBeCreated` 去套娃

- 日期：2026-09-14
- 狀態：**已執行完成**（2026-09-14；Leo `az login` 後由 agent 執行；st 11:25、prod 11:40 PT）。執行紀錄見 §6。
- 為什麼先做這一個：cloud-local-proxy 退役（Phase 1.6 / D8）是整份計劃前置等待最長的一項——「已知 caller 全部改指向 → 兩集群流量歸零 30 天 → scale-to-0 → 再 30 天 → 封存」。雲上那艘 proxy 唯一已知 caller 就是 transv2 的 S1，S1 不改，30 天的計時器根本不會開始。

## 1. 四段分析（change gate Gate 1）

**目的**：transv2 prod 每次 resolve GraphQL 欄位 `if_personalized_report_can_be_created` 都要繞一趟 cloud-local-proxy 才到 on-prem report server；proxy 只是純轉發。拿掉這一跳，同時讓雲上 cloud-local-proxy 的已知流量歸零，開啟退役計時。

**改前（實讀 code + cluster 值）**：
- `LIS-transformer-v2` `src/trans/resolvers/patientProfile.resolver.ts:339`：`getPnsData(process.env.checkIfPersonalizedReportCanBeCreated + String(sample_id))`，`getPnsData` → `tool.ts getRequestv2`：`axios.get(url, { headers: { Authorization: 'Bearer ' + token } })`，非 200 就 throw，resolver catch 後回 `null`；回應先進 Redis（key 含完整 URL）。
- prod ConfigMap `transv2/lis-transv2-config` 該 key = `http://cloud-local-proxy-service.cloud-local.svc.cluster.local:3047/old-report/checkIfPersonalizedReportCanBeCreated?sample_id=`（Appendix B；query string 被去掉，`?sample_id=` 由 proxy 端 `@Query() sample_id` 反推）。
- `cloud-local-proxy` `src/old-report/old-report.controller.ts:878`：`UnifiedAuthGuard` 驗 Bearer → `oldReportService.checkIfPersonalizedReportCanBeCreated(sample_id)` → `process.env.CheckIfPersonalizedReportCanBeCreated + sample_id` = `http://192.168.60.77:8081/secure/nologin/CheckIfPersonalizedReportCanBeCreated?sampleId=` + id，`axios.get`（header `Authorization: Bearer ` 空字串）→ 把 on-prem 的 body 與 status 原樣回給 transv2。**沒有任何轉換**。
- `LIS-transformer` v1 prod 同名 key 已直指 `http://192.168.60.77:8081/secure/nologin/CheckIfPersonalizedReportCanBeCreated?sampleId=`（`docs/proxy-migration-configmap.md:25`），`src/proxy/old-report.service.ts:647` `axios.get(url)` 不帶 header。
- Datadog（7 天）：`service:lis-transv2-deployment env:prod` 對 `cloud-local-proxy-service...:3047/old-report/checkIfPersonalizedReportCanBeCreated` 的 http.request span 全部 200，單跳約 70–110 ms；transv2 這 7 天沒有「Error checking if personalized report can be created」的 error log（count 0）。

**改後為何有效**：新值就是 proxy 內部組出來的那個 URL，caller 一樣是把 sample_id 直接接在後面，所以 on-prem 收到的 request 一模一樣；proxy 對回應零轉換，所以 transv2 收到的 body / status 也一模一樣。唯一差異是 on-prem 會多收到 transv2 的 `Authorization: Bearer <user token>`——已實測該端點對這個 header 不敏感（§2）。少一跳 HTTP + 少一次 proxy 端 JWT 驗證。

**改什麼**：只改 ConfigMap 一個 key 的值，再 rollout restart 讓 pod 重新讀 env（`envFrom configMapRef`，啟動時注入）。零 code 變更。先 staging（`lis-transv2-config-st` / `lis-transv2-deployment-st`），比對後再 prod。

## 2. 已完成的驗證（2026-09-14，本機 VPN）

| 檢查 | 結果 |
|---|---|
| 目標值 | v1 migration doc 給出完整字串（含 `?sampleId=`）；與 Appendix B cloud-local ns 的 `CheckIfPersonalizedReportCanBeCreated` host/path 一致 |
| on-prem 端點可達 | `nc 192.168.60.77 8081` OK |
| header 敏感度 | `curl ...?sampleId=0` 不帶 header → `200 false`（77 ms）；帶 `Authorization: Bearer not-a-real-token` → `200 false`（65 ms）。body 與 status 相同 |
| transv2 ns → on-prem 網路 | transv2 prod 已在用 `KAFKA_BROKER_carlos1/2 = 192.168.60.9/10:9095`（`calendar/.../kafka.service.ts:23`），同一 on-prem 網段有活路；60.77:8081 這一條由 §3 的 in-pod readback 最終確認 |
| proxy 是否轉換 | 否：`res.status(result.code).send(result.result)`，原樣轉發 |
| 快取 | Redis key 含 URL，換值後只是冷一次，無正確性影響 |

## 3. 執行步驤

腳本：`scripts/phase1-s1-repoint.sh`（dry-run 預設；`--apply` / `--rollback`）。備份含 secret，寫到 `~/.trans-opt-backups/`，不進 repo。

1. `az login`（Leo，互動式；見 §5）
2. `scripts/phase1-s1-repoint.sh st` — dry run，確認 staging 現值（預期 `https://www.vibrant-america.com/lisapi/v1/lis/cloud-proxy/old-report/checkIfPersonalizedReportCanBeCreated?sample_id=`）
3. `scripts/phase1-s1-repoint.sh st --apply` — 備份 → patch → rollout restart → 在新 pod 內 `env | grep` + `node http.get` 打新 URL（sampleId=0 預期 `200 false`）
4. staging 用真實 sample 走一次 GraphQL `if_personalized_report_can_be_created`，與 prod 同 sample 的回傳比對（或直接 curl 新舊兩個 URL 比對 body）
5. `scripts/phase1-s1-repoint.sh prod` → `--apply`（3 replicas RollingUpdate maxUnavailable 25%，不中斷）
6. 30–60 分鐘後 Datadog：
   - `service:lis-transv2-deployment env:prod @http.host:192.168.60.77` 出現、`@http.host:cloud-local-proxy-service*` 這條 path 歸零
   - `"Error checking if personalized report can be created"` log 仍為 0
   - proxy 端 `/old-report/checkIfPersonalizedReportCanBeCreated` 進站 span 歸零
7. 更新 Appendix B 的 transv2 兩個 ConfigMap 基線（Phase 0.5），PLAN §2.4 S1 改判定為「已去套娃」

## 4. 回滾

`scripts/phase1-s1-repoint.sh <st|prod> --rollback`：把 `~/.trans-opt-backups/<cm>.checkIfPersonalizedReportCanBeCreated.before` 記錄的舊值 patch 回去並 rollout restart。整個回滾約 1–2 分鐘。

## 5. Blocker

```
az login --tenant "e5dd0b3e-e7fe-4892-b807-43591e72c9ea" --scope "6dae42f8-4368-4678-94ff-3960e28e3630/.default"
```
在 Claude Code 提示列用 `! ` 前綴執行即可（互動式 MFA）。登入後告訴 agent 一聲，agent 接著跑 §3 步驟 2–7。

## 6. 執行紀錄（2026-09-14 PT）

| 步驤 | 結果 |
|---|---|
| 改前實讀 | prod 值 `http://cloud-local-proxy-service.cloud-local.svc.cluster.local:3047/old-report/checkIfPersonalizedReportCanBeCreated?sample_id=`；st 值 `https://www.vibrant-america.com/lisapi/v1/lis/cloud-proxy-st/old-report/checkIfPersonalizedReportCanBeCreated?sample_id=` |
| 網路預檢 | 改之前從 st pod 與 prod pod 各 `node http.get` 直打 60.77:8081 → `200 false`，72–77 ms |
| staging apply | 11:25 backup → patch → rollout（1 replica）→ 新 pod `lis-transv2-deployment-st-55d4994694-cjn5g` env 正確、GET `200 false` |
| 等價比對（prod pod 內，舊路帶 pod 內 `token` 過 proxy 的 UnifiedAuthGuard） | 39 個最近被存取的 sample：38 個 `200 false` 兩路全同；`abc` 兩路皆 500（proxy 回空 body、on-prem 回 HTML 錯頁；v2 `getPnsData` 非 200 一律 throw → resolver 回 `null`，行為相同）。掃 2100000/2300000/2450000/2550000 各 150 個 id 找到 31 個回 `true`，取 20 個比對兩路全同。avg 單跳 73 ms → 41 ms |
| prod apply | 11:40 backup → patch → rollout restart（3 replicas RollingUpdate，約 2.5 分鐘，全程有 ready pod）→ 新 pod `66b88c9f56-*` ×3 Running；readback env 正確、GET 2100012 → `200 true`、2634446 → `200 false` |
| 注意 | 腳本第一版 readback 選到了正在終止的舊 pod（status 短暫顯示 Error，是舊 replica 收 SIGTERM 的退出碰；pod 隨即被回收，未能保留其 log）。已改為選最新 pod |
| after 驗證 | 見 §7（Datadog） |

## 7. After 驗證（Datadog，prod rollout 完成後 12 分鐘內，2026-09-14 18:28–18:40 UTC）

| 檢查 | 結果 |
|---|---|
| 新路 span | `service:lis-transv2-deployment env:prod @http.url:*CheckIfPersonalizedReportCanBeCreated*` 12 筆（indexed），`http.host:192.168.60.77`，全部 200，40–70 ms |
| 舊路 span | `@http.url:*cloud-local-proxy*checkIfPersonalizedReportCanBeCreated*` 最後一筆 18:26:31 UTC（rollout 進行中、來自尚未終止的舊 pod），之後 0 筆 |
| resolver / HTTP helper 錯誤 | `"Error checking if personalized report can be created" OR "Error getting requestv2"` 15 分鐘內 0 筆 |
| pod log | 三個新 pod 起來後 8 分鐘內 0 筆 personalized-report / ECONNREFUSED / EHOSTUNREACH / ETIMEDOUT |

結論：S1 去套娃完成，雲上 cloud-local-proxy 的已知 caller 歸零。Phase 1.6(d) 的「流量歸零 30 天」計時自 2026-09-14 起算；未知 caller 仍要靠 ingress access log（D5）確認。
