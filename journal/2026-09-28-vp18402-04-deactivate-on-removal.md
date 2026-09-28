---
date: 2026-09-28
slug: vp18402-04-deactivate-on-removal
related: [VP-18402, VP-18404, PH-917, SIIR-293, VP-18403, QH-7271, QH-7275, LBS-1784, LBS-1785, LIS-7716, VP-17120, VP-18055, VP-18216]
distilled: false
---

# VP-18402 / VP-18404 — 移除 provider 時停用其 EMR integration

兩張票一起做完並上 prod，03 天後由 Leo 指示轉 Done。這篇記的是三個「我自己造出來的問題」，
因為技術結論本身在 STM 裡已經很完整。

## 探索過什麼

從 PH-917 / SIIR-293 往下讀，先確認真正的機制：`resolveOrderingIntegration` 只看
`status='LIVE' AND ordering_enabled=true`，**完全不看 provider-clinic 關係**。這一句是整件事的
根。result push 那邊同樣是 `status='LIVE'` 過濾（9 個點），所以停用會連帶停掉在途報告 —— 這是
問 PM 的題目，Leo 答「不送」。

trans 側先掃清楚：`removeCustomerFromClinic` 不是一個函式，是**兩個呼叫點**
（`utility.service.deleteCustomerProfile` 和 `setting.practiceInfo.service.removeInvitation`），
而且 trans **從來沒有呼叫過 emr-v2**，這會是第一條相依。

core 那邊讀了 Go 的 `RemoveCustomerFromClinic`，發現它**即使 customer 根本不在該 clinic 也回
200**（刻意對齊 v1）。所以「core 回 200」不能當作「真的移除了」的證據。

## 排除過什麼，為什麼

- **`GetCustomerClinicNames`** 排除：它只回 clinic **名字**，用名字比對不是身分驗證。改用
  `ListClinicCustomerDetailsByClinicID`（VP-18216 的 thick 版）。
- **在 emr-v2 端加 clinic 成員 cache** 排除：core 自己在移除時會清它的 clinic cache
  (`InvalidateCustomerClinicNamesCache`)，我再加一層就是一層沒人控制失效的 cache。
- **fail-closed** 排除：order 熱路徑上一次 gRPC deadline 會停掉全實驗室收單。改 fail-open +
  第三個明確狀態 `check_unavailable`，讓「檢查過」和「檢查不了」在 log 裡分得開。
- **沿用 `customer_not_found`** 排除：它在 VP-17120 之後是 retryable，會燒完 retry 再進 triage，
  而且長得跟「這 provider 缺 integration」一模一樣 —— 等於引導值班的人把洞重新打開。

## 為何這樣決定

`findMany` 而非 `findFirst` 是 LBS-1785 直接教的：prod 有過相隔 7 秒的兩列一模一樣的 LIVE
（`create()` 沒有 uniqueness guard，LIS-7716 還開著）。後來 staging 實測也確認一堆 (customer,
clinic) 各有 2 列 —— 用 findFirst 會只停一半，bug 還在。

路由宣告在 `@Patch(":id")` **之前**：NestJS 照宣告順序比對。這件事後來在 prod pod 的啟動 log 裡
被真實證實（`deactivate-clinic-member` 先於 `:id` 註冊），也順帶發現**不能用 HTTP 狀態碼判斷新舊
版本** —— 舊 image 打新路徑一樣回 401，因為 `:id` 把字面路徑當成 id 接走、guard 先跑。

## 我自己造出來的三個問題（本篇重點）

### 1. 為了風格一致而 over-engineer

trans 側我把它做成 `@Injectable` service，理由只是「跟 `charge-balance.service.ts` 一致」。那個
選擇**本身**製造了全部的膨脹：4 個 module 註冊、一支 DI spec、改一個既有 spec、一次 push gate
失敗。Leo 一句「不是很簡單的 url endpoint 讓 trans call 就好了嗎」直接戳破。

改成 module-level 純函式後：**8 檔 +105 → 2 檔 +21**，零 module 改動，DI 那整類 bug 從結構上
消失。

延伸的一課：我原本在每個呼叫點加 try/catch 來防「service 保證不 throw 但不能押在那上面」。
純函式版把整個 body 包進一個 try/catch，讓那個保證**在結構上為真**，呼叫端就不需要防禦了。
與其在每個使用點加保護，不如讓契約本身不可能被違反。

### 2. `git add -A` 把 generated 檔案掃進 PR

跑了 `npm install` 補一個缺的依賴，prisma 的 postinstall 重新產生了**版控中的**
`prisma2/generated/`，我接著 amend 時用 `git add -A` 沒重看 status，把 12 個檔案（含三個
100MB+ 的 binary）推上 PR。沒有任何 gate 擋到 —— pre-push hook 檢查 build 和 DI，不看 diff 內容。

是 Leo 問「這是對的嗎」我回頭看 `git diff --stat` 才發現。

### 3. PR base 選錯，diff 變成 20000 行

`LIS-transformer` 的 `main` 和 `stage_test` 是**雙向分岔**（165 / 105 commits）。我從 main 切
分支卻 target stage_test，GitHub 就把兩條線的全部差異渲染出來：137 檔、+18580、CONFLICTING。
我的改動一直是 5 檔 +372。

repo 的既有慣例是**一個改動兩個分支兩個 PR**（`{name}` → main、`{name}-stage` → stage_test），
我只做了一個還指錯 base。

## 驗證做對的部分

prod baseline 之前一直拿不到（本機到 DB 全 ETIMEDOUT、vibrant MCP 整組掛掉），最後是**在
emr-v2 的 pod 裡跑 node** 解決的 —— 那裡同時有 prisma client 和 gRPC client。量出 1013 列 LIVE
裡 73 列 stale，再逐層收斂到「只有 1 列在活躍 ordering path 上，而那個 provider 近 90 天零
order」，所以 gate 上線不會擋到任何真實流量。這個結論後來被三天的實際數據證實（0 次拒絕）。

寫入驗證做了 100% + **全表反向查核**（近 10 分鐘 `updated_at` 變動的列，整張表只有那 2 列；
history / note 各正好 2 列）。

## Leo 的原話

- 「1. 不拆 2. 不送(只要remove 就移除, 後續收到訊息就看是不是當下還是live) 3. 不 backfill
  4. ok, 5 不管FE」
- 「有確保如果customer本來就沒有integrate 會seamlessly不處理也不報錯嗎？」
- 「LIS-transformer 有需要改這麼多嗎？不是很簡單的 url endpoint 讓 trans call 就好了嗎」
- 「PR 838 改了約20000行，這是對的嗎？而且還有conflict」
- 「那就用image 測試」
- 「沒關係不需要做，把已經做完的轉done(不要轉別人的ticket)」

## 值得記住的操作細節

- **worktree 共用 node_modules 會出事**：`@prisma/client` 是從 per-branch 的 schema **產生**的，
  主 checkout 在舊 branch 時，worktree 借它的 client 會出現 5 個幻影 type error。給 worktree
  自己的 `.prisma` / `@prisma` 實體目錄再 `prisma generate` 才對。
- **zsh**：`origin/$b:src/...` 裡的 `:s` 會被當成 history substitute modifier，路徑被悄悄改寫
  成別的東西。一定要 `origin/${b}:src/...`。這次害我誤報兩次「code MISSING」。
- **診斷指令不要 `2>/dev/null`**：我在 `git fetch` 後面吞掉 stderr，結果拿舊 ref 去比對，
  自己製造假警報。
- **before/after regression 比對對「兩邊都跑不起來的 suite」沒有證據力**。`@azure/event-hubs`
  在 package.json 但本機沒裝，7 個 suite 根本沒執行。我說「前後失敗的一樣」是真的但無意義；
  裝好之後才發現其中一個是我弄壞的。要數的是**實際執行的 suite 數**，不只是狀態有沒有變。
- **emr-v2 有 global prefix `api/v1`**：`EMR_V2_BASE_URL` 不帶它就全部 404。
- **`lis-trans-config` 的 repo 檔案 `lis-trans-k8env.yml` 只有 5 個 key，live 有 162** ——
  它不是 apply 來源（last-applied 有 133 個且含該檔沒有的 key）。真正的來源不在這個 repo，
  至今沒找到。

## 收尾時的已知缺口（Leo 決定不補）

- VP-18404 的**成功路徑在 prod 從未觸發過** —— 三天內沒有任何 provider 移除事件。只有單元與
  函式層驗證，沒有一次真實端到端。
- order path 的 gate **沒有 kill switch**，pod 一 roll 就生效。這次零影響是我部署**後**才量出來
  的，是運氣不是設計。
