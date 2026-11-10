# Announcement — trans v1 /trans and /utility route removal (VP-18478)

For Leo to send in Slack #developers (C02AQGMU422). Written 2026-11-09 after PR #1119 reached prod
(image bae4d453) and the caller log was verified searchable. Deadline = two weeks after posting.
`/utility/confirmAddress` is deliberately NOT in the list: 8,544 calls in 30 days, and its target
(`lis-shipping-service.shipping.svc.cluster.local:16256`) is in-cluster only, so there is no replacement
a browser can call yet.

---

*trans v1 會在 2026-11-23 移除下列 15 條 route*

以下 route 過去 30 天流量都是 0（`queryForeignLink` 只有 1 次），不是純轉手就是死碼／測試用。11/23 之後呼叫會拿到 404：

*純轉手*
• `GET /trans/checkIfPersonalizedReportCanBeCreated`
• `GET /trans/getOrderSummaryReportZip` → 改用 `GET /trans/GenerateOnlineZipDownloadV2`
• `GET /utility/ifConfirmAddress` → 改用 `GET /utility/ifConfirmAddressV2`
• `PUT /utility/updateCollectionStatus`
• `GET /utility/queryForeignLink`

*死碼／debug*
• `GET /utility/getSalsesCustomers`、`GET /utility/getSalesCustomers`
• `GET /utility/newkaf`、`POST /utility/findch`、`POST /utility/read`、`POST /utility/pay`
• `GET /utility/transpnssettingtocore`、`POST /utility/uploadCertification`
• `GET /utility/getInventoryPage`、`GET /utility/rsatest`

有在用的話，11/23 前在 VP-18478 留言。從今天起每次呼叫都會記下呼叫端，有人打到我們會直接找你。

Ticket: https://vibrantamerica.atlassian.net/browse/VP-18478
