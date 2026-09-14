# Phase 1.4 — S2 runbook：transv2 `proxy_*` 三支改直連 gRPC（去套娃）

- 日期：2026-09-14
- 狀態：**code 完成、PR 待 review**（LIS-transformer-v2 branch `feature/leo/TRANS-OPT-S2-grpc-direct`，base `main`）。merge 後預設行為不變；切換靠 ConfigMap。
- 定位：**去套娃，不是 p95 手段**。量測（`PLAN.md` Phase 2 表、`phase1-s1-runbook.md`）顯示 PatientProfileSlow 的尾巴在 shipping / interactive-report，S2 三跳 p95 只有 0.25–0.52 s 且與其他 downstream 並行。拿掉它省的是 transv2 → v1 這一趟 HTTP + v1 的 JWT 驗證 + v1 pod 的 CPU，並讓 v1 少掉 `/proxy/grpc/*` 這組被自己人打的路由。

## 1. 四段分析（change gate Gate 1）

**目的**：transv2 有 6 個地方拿 kit status / test status / questionnaire 時，是打 HTTP 到 trans v1 的 `/proxy/grpc/getKitStatus|getTestStatus|getQuestionaireBySampleId`，v1 再用 gRPC 打 shipping / test-connect。transv2 自己就有同一組 gRPC client 與相同的 `SHIPPING_RPC` / `TEST_RESULT_RPC` 位址（prod ConfigMap 值與 v1 相同：`lis-shipping-service-grpc.shipping.svc.cluster.local:63142`、`lis-test-connect-grpc-service.results.svc.cluster.local:6889`）。

**改前（實讀）**：
- 呼叫點：`patientProfile.service.ts` 730（`patientOrderInfo`，FedEx warning 才呼叫）、986（`patientKitInfo`）、1568 / 1588 / 1638（`getSampleWithQuestionnaireReport`，三支同一個 `Promise.all`）走 `utilityAPIService.getPnsData(process.env.proxy_* + sample_id, context)`：Redis 10 s cache（key 含 caller identity hash + URL）→ axios GET 帶使用者 Bearer → 非 200 throw `upstreamGraphQLError`。`utility/utility.service.ts` 2582（`UtilityRestService.getKitStatus`，skin 流程）另用 axios 直打 + 自己的 `lis_trans_skin_kitStatus_*` 3600 s cache，失敗回 `null`。
- v1 端（`LIS-transformer/src/proxy/proxy.controller.ts` + `proxy.service.ts`）：`CustomJwtAuthGuard` 驗 token → `createMetadataForCoresampleV2(request_id, req.user.userId)` 組 metadata（authorization = OAuth2 client-credentials、x-request-id、service-name、ip、user-id）→ `ShippingService.getKitStatusBySampleId({sample_id})` / `TestResultGrpcService.getTestStatus({sampleId: Number})` / `ShippingService.getQuestionaireBySampleId({sample_id})` → **getKitStatus 把 `send_out[i].packages` 缺值補成 `[]`**（proto3 空 repeated 不上線；Sentry #68038）→ Nest 直接回傳物件（JSON 序列化）。
- v2 的 `protos/shipping.proto` 比 v1 少 `GetKitStatusBySampleId`、`GetQuestionaireBySampleId` 兩個 rpc 與 `SampleId` message；`tests.proto` 兩邊相同。兩邊 gRPC loader 選項相同（`keepCase: true`）。

**改後為何有效**：新 `ProxyGrpcService` 逐行移植 v1 的三個方法（含 packages 正規化、含 metadata 的五個 header），回傳前做一次 `JSON.parse(JSON.stringify())` 讓形狀與走 HTTP 回來的完全一致。`TRANS_PROXY_GRPC_MODE` 三段切換：`http`（預設，原路）→ `shadow`（兩路都打、回 HTTP 結果、log `proxy_grpc_shadow` 記 equal / diff path / 各自耗時）→ `grpc`（直連，沿用同一套 10 s identity-scoped Redis cache，錯誤包成同一種 `upstreamGraphQLError` 讓所有 call site 的 `.catch(() => default)` 行為不變）。shadow 是在真實全量流量上證明等價（customer-agnostic），不是抽樣比對。

**改什麼**：
| 檔案 | 變更 |
|---|---|
| `protos/shipping.proto` | 補齊與 v1 相同（+2 rpc、+`SampleId`） |
| `src/trans/services/proxy-grpc.service.ts`（新） | `ProxyGrpcService`、`resolveProxyGrpcMode`、`canonicalJson`、`diffPaths` |
| `src/trans/services/utility.api.service.ts` | 注入 `ProxyGrpcService`；新增 `getProxyKitStatus` / `getProxyTestStatus` / `getProxyQuestionaire` 與模式分派、shadow log、grpc cache |
| `src/trans/services/patientProfile.service.ts` | 5 個呼叫點改用上面三個方法（不再讀 `process.env.proxy_*`） |
| `src/utility/utility.service.ts` | `UtilityRestService.getKitStatus` 三模式分派，保留原 3600 s cache 與 `null` 降級 |
| `trans.module.ts` / `utility.module.ts` / `dashboard.module.ts` | 註冊 provider |
| specs | `proxy-grpc.service.spec.ts`（16）、`proxy-lookup.spec.ts`（11）、`utility.service.spec.ts` +5、`utility.api.service.spec.ts` 建構子補參數 |

零行為變更的證據：預設 `http` 時 `getProxyKitStatus` 等就是呼叫 `getPnsData(同一個 URL, context)`，spec 逐一驗證 URL 與 context 原樣、gRPC 不被呼叫、錯誤原樣拋出。

## 2. 切換與驗證步驤

1. PR merge → main 自動部署 prod（模式 `http`，行為不變）。
2. `kubectl -n transv2 patch cm lis-transv2-config-st --type merge -p '{"data":{"TRANS_PROXY_GRPC_MODE":"shadow"}}'` + rollout restart st；再對 prod 同樣設 `shadow`（shadow 對使用者零影響，只多一條 gRPC 與一筆 log）。
3. 跑 24 h 後 Datadog：`service:lis-transv2-deployment @operation:proxyGrpcShadow` 依 `@method` 聚合 `@equal`、`@grpc_ok`、`@http_ms` vs `@grpc_ms`。**通過條件：equal 100%（diff_paths 為空）、grpc_ok ≥ http_ok**。任何 diff 先查原因（最可能是 int64 / enum 表示法差異），沒查清不切。
4. 通過 → `TRANS_PROXY_GRPC_MODE=grpc`（st 先、prod 後）+ rollout restart。
5. 觀察 24 h：transv2 對 `lis-trans-service:3146/proxy/grpc/*` 的 span 歸零；resolver 錯誤 log 不升；`patientProfile` operations p95 不變（預期）；v1 `/proxy/grpc/*` 進站量下降。
6. 穩定一週後另開 PR 移除 `http` / `shadow` 分支與 `proxy_*` ConfigMap key（S6 一併清）。

## 3. 回滾

任一階段：`TRANS_PROXY_GRPC_MODE` 改回 `http`（或刪 key）+ rollout restart，1–2 分鐘。code 不必 revert。

## 4. 注意事項

- draft PR #626（comments only）在同一批行上加了 `TRANS-OPT [P1-S2]` 註解，會與這個 PR 衝突；S2 做完後那些註解已無意義，建議關閉 #626 或 merge 這個 PR 後重開。
- shadow log 只記 diff 的路徑與 sample_id，不記值（避免 tracking number 等內容進 log）。
- gRPC 失敗在 `grpc` 模式包成 `upstreamGraphQLError`，`func = proxy_grpc_<method>`、`upstreamPath = /<method>`，Sentry 會與 HTTP 時代的 `get_pns_info` 分開分組，這是刻意的。
- `daily-report.service.spec` 在整包平行跑時仍偶爾超過 15 s（單跑 6 s 全過），與本 PR 無關，但 Phase 0.2 的 timeout 調整沒有根治，需另查。
