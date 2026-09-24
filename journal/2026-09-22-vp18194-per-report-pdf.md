---
date: 2026-09-22
slug: vp18194-per-report-pdf
related: [VP-18194, PH-907, SIIR-291, QH-7066, VP-18138, VP-17344, VP-17493, VP-17715, LIS-7716]
distilled: true
distilled_on: 2026-09-24
---

# VP-18194 — per-report PDFs to EMR-integrated practices

## 探索過什麼

從 ticket + PH-907 + SIIR-291 三張票拼出真實需求：兩個夥伴各自要求「一張多項目的單，一份報告一個
PDF」，而不是現在那一份合併的大檔。PH-907 已經給了技術路徑（`getReportStatusListV2` 取清單 →
`sections=` 組報告 URL → 丟給 report-pdf-engine），所以探索重點放在「這條路徑是真的嗎」與「交付層
要改哪裡」。

派了兩個 Explore agent：一個掃 emr-v2 的推送管線與附件基礎設施，一個掃 LIS-Report / report-pdf /
report-pdf-engine。同時自己對 prod 做讀取驗證。

## 排除過什麼，為什麼

- **PH-907 說 Cerbo 是「API-based attachment delivery」——這是錯的。** 查 prod：Cerbo 就是 vendor
  `MDHQ`，走 SFTP，Maristany 的檔案丟 `/eduardomaristanymdemr/results/`。整張票的交付設計如果照這句
  話走會整個歪掉。PM 轉述的 vendor 技術細節要 sanity-check，這是 LTM 裡已有的教訓再次成立。
- **HL7 內嵌多份 PDF（把每份報告掛到對應 panel 的 OBR 底下）** 排除。實際看了 prod 的 HL7：合併 PDF
  掛在一個合成的 `VAPDF^Vibrant PDF Report` OBR 底下，而 encoder 結構上只能帶一份。要改成 N 份會動到
  所有 vendor 共用的編碼路徑，而且「Cerbo 的 parser 吃不吃得下」只有 Cerbo 能回答。Leo 裁決「用散裝
  直接丟」之後這條就不在範圍內了。
- **`getSelectedReportsZip`（Step 4 的方案，且撐過了 PRO/CON 辯論）** 在實作時被推翻。見下。
- **把功能做成 `result_push_level=PER_REPORT` 的延伸** 排除：push level 是 HL7 的切分粒度，而
  Maristany 是 WHOLE_ORDER 卻正是第一個要分拆 PDF 的客戶——那個組合在這個設計下表達不出來。
  最後的形狀是兩者正交：push level 決定時機，新開關決定內容。

## 為何這樣決定

**failure shape 推翻了辯論結果。** 兩條取得路徑的 happy path 幾乎一樣，辯論雙方也只辯 happy path。
我實測壞輸入才發現：zip 那條的參數打錯回 200 + 合法 `%PDF-` + 4 KB 空殼，單項那條回 500。ticket 自己
的驗收條件是「failures logged without sending an incorrect or mismatched file」，而被辯論選中的方案
可以一邊違反它一邊回報成功。換成單項端點之後，還順帶消掉「要在我方複製 flag 文法」「zip entry 用長名
要回推代號」「repo 沒有 zip 套件」三件事。

**反方（CON）的三個實質貢獻都用 prod 查證過才採納**：附件表的 FK 是 NOT NULL（推翻獨立觸發路徑）、
62/202 的 MDHQ 診所有多列 LIVE（推翻讀某一列的設定，改成對投遞目的地取 OR）、Cerbo 取檔後搬 archive
（推翻「同名重送 = 冪等覆寫」）。反方另有一條事實是錯的（說 status list 沒有長名），照查證駁回。

**amended 那條是先量再答。** Leo 第一次說「我不懂問題，把這個人設定成好了就發不行嗎」，我沒有再解釋
一次，而是去 prod 撈真實的修訂紀錄：有一種會連結果重新核可、重發完成事件（會自己重送），另一種只發
內部快取清除（我們收不到）。量出來之後 Leo 給了「以前的不管了，只做未來的」這條跨 ticket 規則，而
那是在資訊完整的情況下做的裁決。

## Leo 的原話

- 「1. 用散裝直接丟 2. 我不懂問題，就是把這個人設定成只要好了就發separate report不行嗎？」
- 「以前的不管了，只做未來的(這點很重要是accross ticket的)」 ← 跨 ticket 規則
- 「就是等report完成後去看說是不是要per report 發 pdf, 如果是的話就發多個, 只是這樣」
- 「要 push, 另外直接改staging + production 的db (DDL)」
- 「The acceptance criterion ... is not implemented... 這是什麼意思？」 ← 追問之後才發現要把
  「這是既有的洞、不是這次改壞的」寫進 Jira comment
- 「ok 發，並且使用這個ticket 要求的那個customer 作為canary」

## 值得記住的操作細節

- prod Azure MySQL 有 `--require_secure_transport=ON`：mysql2 要用從 URL 拆出來的 config 物件加
  `ssl`，直接丟 URL 字串會把 ssl 選項吃掉。
- `ALGORITHM=INSTANT` 只允許 `LOCK=DEFAULT`。我為了滿足 linter 的一條警告而加 `LOCK=NONE`，反而
  觸發另一條 critical——為了通過檢查器而做的修改要再跑一次檢查器。
- 在 worktree 裡跑 jest 不能加 `--testPathIgnorePatterns=worktrees`，它會匹配到工作目錄本身。
- 驗證設定生效時，最有說服力的做法是把**部署中的決策函式**載進 pod，餵它部署中的 client 讀出來的那
  一列，而不是自己重算一次同樣的邏輯。
