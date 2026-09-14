# Appendix A — 會議錄音摘要（Trans p1 / p2，2026-09-10 錄製）

> 轉錄工具：mlx-whisper `whisper-large-v3-turbo`，切 5 分鐘片段、`condition_on_previous_text=False`。
> 第一次整檔轉錄在 5 分鐘後陷入重複幻覺，故改分段。轉錄輸出為簡體，本摘要以繁體整理。
> 人名為會議中口語稱呼（志斌、周凡、瑞、浩哥/Hawk、雨萱/宇萱、葉開/Leo），可能有誤。
> 原始逐段文字：`raw-transcript/p1_00.txt` ~ `p1_04.txt`（第一段 0-25 min）、`p2_00.txt` ~ `p2_01.txt`（第二段 0-7.5 min）。

## p1 00:00-05:00 — 開場、目標

- 開會目的：多數人不熟 Trans；志斌、周凡較熟，請他們介紹並回答問題。
- 主要目標是**速度**：看下游一圈能不能並行而不是串行。
- findPatient 的例子：accounting 讓本來就慢的端點更慢（對應 VP-18197）；AI 也發現 accounting 之外還有其他慢點。
- 周凡的例子：Core Info V2 很慢，patient / customer 分別串行拿 name、再打 calendar；改成把幾個 RPC 一起發（`Promise.all`）後明顯變快。
- 態度：Core 側對「Core 的 p95」會自己修；Trans 內部不是 Core 引起的慢，要 Trans 側自己看。

## p1 05:00-10:00 — Trans 的定位、P95、cloud-local-proxy 起源

- Trans 第一個作用：Core 出於**安全（PHI）**而非效能考量，要變成純 RPC 服務，沒有任何外部服務能直接打 Core；前端要拿 PHI 只能經 Trans。第二個作用：為前端聚合（前端一次從 Trans 拿，Trans 再去下游拿）。
- P95 特別高，尤其高峰期；過去 4 小時純高峰期更明顯；很多慢端點，其中有跟 report 相關的。
- 沒人有時間查原因；浩哥看了 Datadog 也不知道為什麼。
- 2023 年剛開 Azure 時，Azure 與本地伺服器之間 DNS 與網路都不通。雨萱起了一個 repo `cloud-local-proxy`：雲上服務要打地上 gRPC、或反過來，都用 HTTP 打 proxy，proxy 在同一集群內再打 RPC。
- 現在雲上可以直接打地上 IP（例：`192.168.60.6:30276` core RPC），但 cloud-local-proxy 仍有流量。
- **套娃**：Trans 有很多一層套一層的現象。Trans 最關鍵的是包 RPC；若一個 Trans 端點從頭到尾只包 HTTP，就沒有存在必要，呼叫方可以直接打目標（例：report、order summary）。

## p1 10:00-15:00 — 套娃實例、三個 aggregator、分工

- 實例：某前端 → cloud-local-proxy HTTP → Trans HTTP → shipping / order HTTP 拿 PDF。完全沒必要，前端直接打 order 即可。
- Datadog 上以 2 秒為標準，有 10 ~ 20 支 API 超標，高峰期更慢。具體原因不知道；「知道的話自己就修了」。
- 現有三個同類 aggregator：Trans v1、Trans v2、LIS-Sample，技術本質都是包別人的東西。Core 的 v1→v2（Nest→Go）與 Order 的 v1→v2 也在進行，gRPC 作為管道；GraphQL 對 Trans 來說並非必要，但已經到這一步就都保留。
- Core 側只以 Core 為中心優化（每個 Core 都有對應的 Trans 路徑，那部分他們會做）；其餘不會主動去看，交給 Trans 側。

## p1 15:00-20:00 — 做法：看 P95 而非修 bug；仿 Core Migration 的流程；Trans 自己的 RPC

- 這種優化不是修 bug，是看 P95（浩哥看到 P95 才有這個想法）。有 bug 當然修，但主軸是慢。
- 流程模式：仿 Core Migration 的 epic——志斌/瑞先建具體 plan；用 AI 產出詳細設計 doc；瑞 review；確定方案沒問題再開票、動工。每個較大的 phase 都出一份 doc。
- Core Migration 的 phase 供參考：先把兩個 DB 鎖成一個 → Shadow → 全模組 Refactor → Shadow 驗證 → read cutover → write migration → 下掉 v1。
- Trans 自己也有 gRPC server（`TransService`），包別人的 HTTP 再以 RPC 提供；有人認為 Trans 本身不該有 RPC，值得檢視（本計劃盤點結果：有 3 個消費者，不可移除）。
- 曾把 Trans 從地上切到雲上時，發現很多「不應該有的東西」。

## p1 20:00-25:00 — 設定 drift 風險、結語

- Trans 的環境變數 100 多個，大部分是服務位址；全公司 developer 都有寫入權。
- 已多次發生：Trans 的 URL 已從地上遷到雲上，再看時又回到地上——有人 `kubectl apply -f` 本機舊檔，沒先拉最新，把別人改過的蓋掉。
- 規範：用 `kubectl edit`、dashboard 改，或 `patch`；非要 `apply` 就先取最新再 patch。Trans v2 有自己獨立的 ConfigMap，同樣適用。
- 結語：Leo（葉開）與 Liu 先定 plan；Trans 裡「看起來像包 report」的端點，若 report 側覺得沒必要，就從 Trans 拿掉，讓前端直打 report。之前 order summary 的包法就完全沒必要。

## p2 00:00-05:00 — cloud-local-proxy 雙向細節

- proxy 是 Azure 與本地網路未打通前的臨時方案，一直沒下掉。凡在 proxy repo 裡的路由都是「通往」某處的中繼。
- 雲上、地上各一套：地上 `60.6` 的 `lis` namespace 也有 cloud-local-proxy；地上服務（例：某 genetics 服務）要打雲上 gRPC（`10.224.0.155`）不通時，打雲上 proxy 的 HTTP；反過來雲上服務要打地上 gRPC，打地上 proxy 的 HTTP（舊做法經 `www.vibrant-america.com/...` 公網）。
- Trans 現在全在雲上，沒有任何地上的部分；但仍經 cloud-local-proxy 繞到地上再打 RPC。
- 呼叫 cloud-local-proxy 的不只 Trans，可能還有其他（例：legacy report / renove report 從地上某 IP 打過來）。

## p2 05:00-07:30 — 具體例子

- 去雲上 transv2 的 namespace 看 `lis-transv2-config`，往下滑可以找到 `checkIfPersonalizedReportCanBeCreated` 指向 cloud-local-proxy——「這明顯就是沒必要的套娃，就算要打 report 也可以直接打」。
- 這些是之前留下的債。散會。
