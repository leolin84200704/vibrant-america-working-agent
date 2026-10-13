# VP-18481 Phase B 白話版：把 LIS-Sample 的「後台機器」搬進 trans

（給 Leo 看的中文版，2026-10-13。英文版 `VP-18481-phase-b-design-note.md` 之後上 Confluence。）

## 一、這件事在做什麼

LIS-Sample 是一個小服務，它有兩種工作：

1. **回答別人的問題**（API）：例如「這支樣本放在哪個架子」。這部分叫 route，Phase C 才搬。
2. **自己默默做的事**（後台機器）：儀器把樣本歸檔後，會丟一張小紙條到 Azure 的「信箱」（Service Bus queue），LIS-Sample 從信箱拿紙條、寫進資料庫，然後再寫一張「我更新了」的紙條到另一個「公佈欄」（Service Bus topic），讓結果系統（results-web）和報表（ClickHouse）知道。還有一個每天早上 9:15 跑的舊資料補抄工作。

Phase B 只搬第 2 種：讓 trans 也有這整套後台機器，**但先關著**。開關沒打開以前，trans 跟以前一模一樣。

## 二、搬了哪些東西

| 東西 | 白話 | 在 trans 裡的開關 |
|---|---|---|
| 四個資料庫連線 | LIS-Sample 本來有六組連線設定，兩組從來沒人用，所以只搬四組 | 沒有開關，一直可用（Phase C 的 route 要用） |
| 信箱的收信員 | 從 `storage-info-updates` 這個信箱拿紙條、寫進資料庫 | `SAMPLE_CONSUMERS_ENABLED` |
| 公佈欄的張貼員 | 每 10 秒把還沒貼的「我更新了」紙條貼到公佈欄；每天凌晨 3 點清掉舊紙條 | `SAMPLE_CONSUMERS_ENABLED` |
| 每天 9:15 的補抄工 | 從舊系統的表再抄一次昨天的歸檔資料 | `SAMPLE_LEGACY_IMPORT_ENABLED`（另一個開關） |
| 排隊用的鎖 | 多台機器同時跑時，用 Redis 排隊避免重複做 | 設定跟 LIS-Sample 完全一樣，所以兩邊會排同一條隊 |

沒搬的：快取（Phase C 跟 route 一起）、Kafka（跟病人資料的 route 一起）、LIS-Sample 那支還沒 merge 的 PR #185。

## 三、為什麼可以這樣搬

- 今天 LIS-Sample 在 prod 有 3 台機器**同時**在收信、同時在張貼。所以「多台一起做」本來就是現況，不需要選一台當隊長。
- 重複做不會壞事：同一張紙條處理兩次，資料庫會因為「同一格只能有一筆」擋掉第二次；公佈欄那邊開了 24 小時內同編號只收一次。
- 程式是**原樣複製**，只改了三處：開關、信箱名稱可以用設定改、補抄工結束時會把 Redis 連線關掉。

## 四、現在的狀態（2026-10-13）

- 程式進了 trans 的 staging（PR #920），staging 那台 pod 正常起來，開關全關。
- staging 的 ConfigMap 已加上需要的設定（四個資料庫位址、Redis、Service Bus 連線字串、開關 = false）。四個資料庫都連得上。
- staging 的資料庫已經建好「我更新了」紙條的那張表（`storage_event_outbox`），之前 staging 沒有這張表。
- 發現一件事：trans 只會印「警告」跟「錯誤」兩種 log，搬過來的程式印的「正常進度」訊息在 trans 上看不到。所以之後驗證不能看 log，要看資料庫跟信箱的數字。

## 五、下一步要什麼

| 誰 | 要做什麼 | 為什麼 |
|---|---|---|
| Tianhao 或 Alex | 在 Service Bus 建 staging 用的信箱 `storage-info-updates-staging`、公佈欄 `storage-data-updates-staging`（建的時候就要勾「重複偵測 24 小時」，之後改不了）、再加一個測試用的訂閱 | 我的帳號只能收發信，不能蓋信箱 |
| 我 | 信箱建好後：staging 開開關，用腳本丟幾張假紙條（新架子、同一張丟兩次、太舊的一張、丟一半把 pod 砍掉），看資料庫跟公佈欄是不是都對 | 這就是票上說的「在 staging 用真的 queue 跑起來」 |
| 我 | 做另一支小 PR，讓 trans 在被關掉時會把信箱連線好好關上（`enableShutdownHooks`） | 現在 trans 關機時不會通知各模組收尾，信箱的「我正在處理」狀態要等 1 分鐘才自動解開 |
| Leo | 決定 trans 上要不要把「收信員開始工作」「處理了一張紙條」這兩種訊息改成警告等級，讓 log 看得到 | 不改也行，只是驗證要看資料庫 |

## 六、prod 要怎麼切（之後的事）

1. prod 的 trans 打開 `SAMPLE_CONSUMERS_ENABLED`。這時 LIS-Sample 跟 trans **兩邊同時收信**，不會有空檔，重複也不會壞事。
2. 看一小時：儀器丟了幾張紙條，資料庫就該多幾筆；信箱裡沒有積壓、沒有被退件的。
3. 要讓 LIS-Sample 不再收信，需要改 LIS-Sample 的程式（它現在只要是 prod 就一定收信），這支 PR 要請有權限的人 merge；或等 Phase C 把 LIS-Sample 整個關掉。
4. 觀察 30 天，LIS-Sample 的機器數量不減。出事就把開關關回 false，重啟，正在處理的紙條最多 5 分鐘內會回到信箱讓 LIS-Sample 撿。
5. 補抄工的開關等 LIS-Sample 那邊的補抄工確定關掉以後再開。

## 七、數字（有需要再看）

- prod 的「我更新了」紙條表：39,405 筆，全部已張貼，沒有卡住的。儀器一天大約 260 張紙條。
- 舊系統的資料庫（on-prem 192.168.60.2）連線上限 400，歷史最高用到 393，所以 trans 連它的三組連線都設成一次只開 1 條。
- 信箱裡有 220 張被退件的舊紙條（2 月和 7 月的），都超過 7 天，收信員拿到也只會直接丟掉，之後清一清就好。
