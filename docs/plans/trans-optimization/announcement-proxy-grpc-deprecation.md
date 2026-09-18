# Announcement — trans v1 /proxy/grpc route deprecation

For Leo to send. Ticket: VP-18320 (due 2026-10-09). Removal date: 2026-10-02.
Formatting uses Slack conventions (`*bold*`); adjust if posting elsewhere.

---

## English

*Deprecation notice — three trans v1 `/proxy/grpc` routes, removal 2026-10-02*

We are removing three routes from trans v1 (`lis-trans-service`) that no longer have a caller:

• `GET /proxy/grpc/getTestStatus`
• `GET /proxy/grpc/getQuestionaireBySampleId`
• `GET /proxy/grpc/listTnpCode`

*Why.* These exist so that trans v2 could reach gRPC services over HTTP. Since the cutover on 2026-09-16, trans v2 calls gRPC directly. Across the full 15 days of request logs we retain, the first two moved in lockstep with a single caller's pattern and dropped to exactly zero the day after that cutover. `listTnpCode` has been at zero the whole time, including before the cutover, and has no caller in any repo we can search.

*What is NOT being removed.* `getKitStatus`, `getPatientTestsResult` and `sendSkinPlacePatientOrders` all stay. The first two still take a small amount of traffic from an in-cluster client we have not identified yet. The third is where `LIS-backend-billing` is being repointed to, so it is a consolidation point rather than a removal candidate.

*If you call one of the three routes above*, comment on VP-18320 before *2026-10-02* and it stays until you have moved. Please do this even if you are not sure — our log retention is 15 days, so a job that runs monthly is invisible to us and this notice is the only way we would find out about it.

*Migrating* means calling the gRPC service directly. Two things have to come with you from trans v1 `src/proxy/proxy.service.ts`, or the move is not equivalent:

1. the metadata construction (`createMetadataForCoresampleV2`) — it propagates the JWT subject to core, and it is not an ownership check;
2. for kit lookups, the proto3 fix-up that turns an omitted `packages` field into an empty array. Leaving that out is Sentry #68038.

`LIS-transformer-v2` PR #629 is a worked example of exactly this migration.

Ticket: https://vibrantamerica.atlassian.net/browse/VP-18320 (due 2026-10-09)
Background: https://vibrantamerica.atlassian.net/wiki/spaces/LIS/pages/2696740867

---

## 繁體中文

*棄用公告 — trans v1 三條 `/proxy/grpc` 路由，2026-10-02 移除*

我們要從 trans v1（`lis-trans-service`）移除三條已經沒有呼叫者的路由：

• `GET /proxy/grpc/getTestStatus`
• `GET /proxy/grpc/getQuestionaireBySampleId`
• `GET /proxy/grpc/listTnpCode`

*原因。* 這幾條的存在是為了讓 trans v2 能用 HTTP 打到 gRPC 服務。2026-09-16 切換之後，trans v2 已經直接走 gRPC。在我們保留的完整 15 天 request log 裡，前兩條每天都跟著單一呼叫者的樣式同步移動，並在切換後隔天降到零。`listTnpCode` 則是 15 天全零（切換前就已經是零），而且在我們能搜到的所有 repo 裡都沒有呼叫者。

*不會被移除的。* `getKitStatus`、`getPatientTestsResult`、`sendSkinPlacePatientOrders` 三條都保留。前兩條目前仍有少量流量，來自一個我們還沒認出來的叢集內 client；第三條是 `LIS-backend-billing` 即將改指過來的目標，它是整併的終點，不是移除對象。

*如果你有在呼叫上面那三條*，請在 *2026-10-02* 之前到 VP-18320 留言，我們會等你搬完再移除。不確定也請留言——我們的 log 只留 15 天，跑月週期的排程對我們是隱形的，這份公告是我們唯一會知道的管道。

*搬移方式* 是直接呼叫 gRPC 服務。有兩樣東西必須從 trans v1 的 `src/proxy/proxy.service.ts` 一起帶走，否則不等價：

1. metadata 的建構（`createMetadataForCoresampleV2`）——它把 JWT 身分往 core 傳，它不是 ownership 檢查；
2. kit 查詢要帶上 proto3 的補值：把線上被省略的 `packages` 補成空陣列。沒帶就是 Sentry #68038。

`LIS-transformer-v2` PR #629 就是這個搬移的完整範例。

Ticket：https://vibrantamerica.atlassian.net/browse/VP-18320 （due 2026-10-09）
背景：https://vibrantamerica.atlassian.net/wiki/spaces/LIS/pages/2696740867
