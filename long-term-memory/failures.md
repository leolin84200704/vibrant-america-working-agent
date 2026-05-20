---
id: failures
type: ltm
category: technical
status: active
score: 0.1448
base_weight: 0.9
urgency: 3
created: 2026-05-20
updated: 2026-05-20
links:
- INCIDENT-20260518
- VP-15460
- VP-16337
- VP-16410
- LBS-1487
- VP-16165
- VP-16424
- VP-16474
- VP-16476
- VP-16251
- VP-16280
- VP-16289
- VP-16423
- VP-16463
- VP-16502
- VP-16154
- VP-16612
- VP-16193
- VP-16232
- VP-16329
- VP-16664
- VP-16617
tags:
- failures
- root-cause
- auto-generated
summary: Auto-aggregated failure index from 36 entries across STM
---


# Failure Index

> 自動生成自 `storage/short_term_memory/*.md` 的 `## Failures` 區段。
> 由 `scripts/extract-failures.py` 維護，手動編輯會被下次 run 覆蓋。
> Last updated: 2026-05-20 — total 36 entries

## Themes

- [DB / migration / backfill](#db-migration) — 8 entries
- [Production side-effects (Kafka / email / SFTP)](#prod-side-effects) — 7 entries
- [Build / TypeScript / Tooling](#build-tooling) — 5 entries
- [Other / uncategorized](#other) — 5 entries
- [Redis / cache / pending list](#redis-cache) — 2 entries
- [Deploy / commit / push coordination](#deploy-coordination) — 2 entries
- [Test / mock / spec](#test-mocking) — 2 entries
- [Scope / requirement / PM communication](#scope-communication) — 2 entries
- [Tool / cwd / branch / repo confusion](#tool-usage) — 1 entries
- [Error handling / throw vs log](#error-handling) — 1 entries
- [Auth / permission / role](#auth-permission) — 1 entries

---

## DB / migration / backfill <a id='db-migration'></a>

### **[[VP-16193]]** — `2026-04-17 18:30` — **insert-order-client.ts script bug: customer_id 設為 clinic_id 值**

- 問題: 執行 insert-order-client.ts 後，order_clients.customer_id = 6338（Practice ID）而非 5408（Provider ID）
- Root cause: script 內部將 customer_id 參數映射到 clinic_id 值，已知 bug
- 修正: 手動 SQL `UPDATE order_clients SET customer_id = 5408 WHERE id = 2278`
- 可預防: 是。未來執行 insert-order-client.ts 後必須驗證 customer_id 是否正確

### **[[VP-16232]]** — `2026-04-20 14:30` — **Failure 1: 用 crm.contacts 而非 gRPC**

- Error: 4,480 筆在 crm.contacts 找不到
- Assumption: crm.contacts 有所有 customer 資料
- Root cause: crm.contacts 只有部分 customer（可能只有 sales contacts），不是權威資料源
- Fix: 改用 gRPC GetCustomer

**Failure 2: 命名格式錯誤**
- Error: 把 patient calendar 改成 "{name}'s Provider Calendar"
- Assumption: 沒有確認現有命名慣例
- Root cause: 沒有先查看已存在的 patient calendar 命名格式（應為 "{NAME}'s Patient Calendar"）

**Failure 3: gRPC endpoint 錯誤**
- Error: CORE_SAMPLE_V2_RPC (10.224.0.53:8084) → ECONNREFUSED
- Assumption: .env 裡的值可以直接用
- Root cause: 沒有先讀 lis-code-agent/knowledge/emr-integration.md，那裡明確記載 gRPC endpoint 是 192.168.60.6:30276
- Fix: 用 knowledge 裡記載的 endpoint

**Failure 4: NestJS createApplicationContext + gRPC**
- Error: gRPC @Client decorator 在 CLI 模式不初始化，且 PublicBookingService.onModuleInit crash
- Assumption: 可以用 NestJS context 跑 gRPC migration
- Root cause: createApplicationContext 不啟動 microservice transport
- Fix: 改用 @grpc/grpc-js + proto-loader 直接建立 gRPC client

**Failure 5: 沒有使用 lis-code-agent knowledge**
- Error: 整個過程都沒有查 knowledge 目錄
- Assumption: 可以靠 .env 和 codebase 自己找到答案
- Root cause: 不知道/忽略了 lis-code-agent 的知識庫系統
- Fix: 任何 gRPC/migration 任務先讀 knowledge/

### **[[VP-16329]]** — `2026-04-27 23:00` — **Failure: 第二次重跑 36816 INSERT 觸發 duplicate constraint error。**

Root cause: 第一次跑時我用 `tail -50` 截取 output，後段顯示 record 資料但沒看到「✅ Successfully inserted」字樣（卡在 record dump），誤判沒成功就重跑。
影響: 無實質影響（script 在 unique check 時擋下，沒 partial insert）。
教訓: 確認 INSERT 成敗應 grep `Successfully|Error|❌` 而非看 record dump。後續 4 個 INSERT 都用 grep 過濾，順利完成。

### **[[VP-16410]]** — `2026-05-06 02:50` — 誤解 Leo「過去的 event 無需更動」為「rollback backfill」

- **錯誤推理**：Leo 說「過去 event 無需更動」我誤解為「backfill 不應該存在」，提議 DELETE 2350 claim + 2670 audit
- **正確意思**：「不要 update / delete 既有 v2_event row」— backfill 進 claim 表的 row 是新表新資料、不是 update 既有 event
- **Leo 糾正**：「未來如果有 accession_id 已經在 claim table 的還要創建 event 需要擋下來」— 暗示 claim table 的歷史資料是必要的（沒 backfill 就沒資料可擋）
- **教訓**：「過去的 event 無需更動」= 不動 v2_event 表本身，**跟 claim table 是否要 backfill 無關**。下次遇到否定句指令要拆「動什麼 / 不動什麼」維度，不要把 scope 自動擴到無關的 table

### **[[VP-16423]]** — `2026-05-04` — insert-ehr-integration.ts 對 25467 的 transaction 全 rollback

- 錯誤：`Duplicate order_client exists for NPI '1356634760' + clinic_id '19583'`
- 當時假設：以為 ehr_integrations INSERT 跟 order_clients INSERT 是分開 step，order_clients fail 不會影響 ehr_integrations。實際 script 用 `prisma.$transaction` 包成一包，order_clients duplicate check 拋 → ehr_integrations 也被 rollback。
- Root cause：script duplicate 檢查依「customer_provider_NPI + clinic_id」（不是 customer_id + clinic_id + ehr_vendor_id），對「同人多 customer_id」case 不友善
- 處理：Phase 2 raw SQL 繞過 check，ehr_integrations 用 cuid library 自生 ID，order_clients 直接 INSERT。
- 預防：未來 ticket 若 provider list 有 same-NPI 重複，先警告 script 對 25467 case 的 order_clients 必失敗，預備 raw SQL fallback

### **[[VP-16502]]** — `2026-05-07` — 抽 helper 沒做（合理 trade-off）

- 5 個 send method cross-recipient loop 結構幾乎一樣（差 templateModel build），原本想抽 helper 集中
- 但每個 method 的 templateModel fields 不同（PRD 7 種 scenario × 2 個 recipient role 的 fields 不互通），抽 helper 要 switch by `(notificationType, recipientType)` 變得 ugly
- 採 in-place duplicate（5 個 method 各加 ~30-50 行）— 雖然 DRY 不滿足但 readability 更高
- 沒算失敗，但記下「複雜 templateModel build 的 cross-cutting helper 抽得不乾淨時，in-place 直白比 helper 好」

### **[[VP-16612]]** — `2026-05-18` — Initial proposed spec was wider than necessary

At Step 4 I proposed `role === 'provider'` (strict). Leo refined to "exclude (clinic_id=150105 AND clinicadmin)". My version would have silently changed patient-role behavior; Leo's preserves it. Lesson: when translating PM natural language ("only X, not Y") into code, prefer narrow exclusion of Y over broad inclusion of X — the former preserves the unconstrained set.

### **[[VP-16664]]** — `2026-05-18` — First-pass YAML schema change

I added `*_timezone` paired fields to both YAML files at Step 5 start, planning to use them in templateModel. Leo immediately reverted with "不能改 yaml file 啊". Root cause: I conflated "BE config describing template variables" with "Postmark template body in Postmark cloud" — Leo treats the YAML AS the template-end contract; adding fields there is an API change even if Postmark template body doesn't reference them. Lesson: when spec says "embed timezone", default to enriching existing values, NOT adding paired fields.

---

## Production side-effects (Kafka / email / SFTP) <a id='prod-side-effects'></a>

### **[[VP-15460]]** — `2026-04-28` — redlock Lock API confusion (#90)

Picked `lock.release()` from redlock@5 docs while installing redlock@4. The two versions have different Lock prototypes (`unlock` vs `release`). Cosmetic in production (TTL covered the leak) but log noise + would have been a real bug if TTL was raised.

### **[[VP-16251]]** — `2026-04-21 21:50` — Script 產出的資料有 3 個問題需手動修正:

1. sftp_ordering_path = null（script 未設定）
2. sftp_archive_path 缺尾部 /
3. sftp_folder_mapping sftp_source_id = null（已修正）
4. 誤插 sftp_folder_mapping result mapping — sftp_folder_mapping 僅用於 ORDER（已刪除）

### **[[VP-16280]]** — `2026-04-23 18:05` — 兩個遺漏（both caught by Leo at review, not by agent）:

- 沒查 `kit_delivery_option` same-clinic 既有 → 預設 `NO_DELIVERY` 與 practice 實際 `BOTH_BLOOD_AND_NON_BLOOD` 不一致
- 沒查 `order_clients.old_clinic_id` → 新 record null，既有皆 1002859
Root cause: Step 5c 只查了 integration-level 欄位（report_option / integration_type / sftp paths），沒把 `kit_delivery_option` 和 order_clients 的 `old_clinic_id` 納入 same-practice-follow-existing 檢查清單。

### **[[VP-16289]]** — `2026-04-23` — - insert-ehr-integration.ts 第一次用錯參數格式 → 看 usage 後修正

- MDHQ 已知問題: sftp_archive_path 缺尾部 `/`、emr_name 小寫 → 手動 SQL 修正

### **[[VP-16423]]** — `2026-05-04` — kit_delivery_option 錯誤對齊 PENDING stub

- 錯誤決定：Phase 2 把 7 筆 ehr_integrations.kit_delivery_option 對齊 17412 PENDING stub 的 BOTH_BLOOD_AND_NON_BLOOD
- Root cause：誤把 PENDING stub（4/23 internal staff 預建、business 欄位全空）當「same-clinic 既有 LIVE」可 follow。實際 stub 的 kit_delivery_option 是 schema default（`@default(BOTH_BLOOD_AND_NON_BLOOD)`），不是真實設定
- prod 驗證：(kits_options=0, kit_delivery_option=NO_DELIVERY) 配對有 112 筆全部一致；其餘 (kits_options=0, BOTH) 579 筆是 schema default 沒明確覆蓋
- 正確規則：**kit_delivery_option 應對齊 order_clients.kits_options（runtime source of truth）**，0 → NO_DELIVERY
- 處理：`_apply-vp16423-kit-fix.ts` UPDATE 7 筆 → NO_DELIVERY（pre-check 通過）
- 預防：(a) PENDING / stub record 不算 same-clinic 既有可 follow；(b) 任何 ehr_integrations.kit_delivery_option 決策都先 check 對應 order_clients.kits_options 對齊

### **[[VP-16463]]** — `2026-05-13 15:46` — v2 NO_NPI parity break (RED FLAG, awaiting user decision)

Two post-expansion files stuck on v2 path with behavioral divergence from v1:

| file id | folder | received | customer_not_found | parse_finished | sample_id | retry_num | pod_name |
|---|---|---|---|---|---|---|---|
| 6053 | parsley-la | 2026-05-13 11:45 | NO_NPI | 0 | NULL | 5 | NULL |
| 6058 | ravelhealth | 2026-05-13 15:30 | NO_NPI | 0 | NULL | 5 | NULL |

**Past 7d MDHQ baseline** (31 success + 9 `no payment method` flags): ALL 40 v1-processed files have `last_update_pod_name='lis-emr-prod-*'` and `parse_finished=1` (even with non-success flags). NO files in entire 7d have `NO_NPI` flag — these 2 are unique.

**Three suspected v2 regressions**:
1. **NPI-check parity break**: v1 either skips NPI lookup or uses a different fallback. v2 explicitly rejects on missing NPI.
2. **Terminal-state retry bug**: v2 detected customer_not_found but didn't set parse_finished=1, so worker keeps retrying (5 attempts). v1 sets parse_finished=1 even with flag.
3. **Audit gap**: v2 worker not persisting `last_update_pod_name` on error path — cannot prove provenance.

**Cutover monitor cadence tightened to 30min** while red flag active.

**User decision options pending**:
- A: Rollback id=78/201 to use_v2_pipeline=0 (let v1 reprocess)
- B: Inspect HL7 file content for NPI presence (rule out data vs logic)
- C: Keep observing

DO NOT auto-rollback without explicit user approval.

### **[[VP-16502]]** — `2026-05-07` — AC4 過度字面化 PRD #3

- **錯誤推理**: PRD #3 寫 "Reminder 48h/24h/15m (To Provider)" 我直接讀為 "only Provider"，加 filter 後破壞 VP-16391 deployed 的「reminder 發所有 participant」設計
- **正確意思**: PRD 字面是「at minimum Provider」— Lab Team 也要收
- **Leo 糾正**: 「需要給 provider + clinician」
- **教訓**: PRD wording 沒 explicit "only X" 時不要加 filter，先確認語意；deployed prod 行為是 evidence，AC 跟既有 test 衝突優先 raise 再決定，不要「先加 filter 等 test 改」

---

## Build / TypeScript / Tooling <a id='build-tooling'></a>

### **[[INCIDENT-20260518]]** — [2026-05-18 後續] 看到 c0852d0 部署後 Leo 仍見舊行為，沒立刻意識到 image age

**錯誤**：看到 prod log 還有 `Using fallback data` 就以為 fix 沒效。
**實際**：prod pod 還沒 rollout，跑的是舊 image。Image build + push + pod restart 大約 15-20 分鐘。
**Preventable**：是。下次 deploy 後先 `kubectl exec ... grep -c <新 marker> /app/dist/...js` 驗證 dist 真的有新 code。

### **[[VP-15460]]** — `2026-04-27` — Wrong proto file edited initially

Edited `src/proto/customer.proto` (`package lis`, legacy LIS host) before realizing v2 RPC lives in `src/proto-v2/customer.proto` (`package coresamples_service`, coreSamples host). Reverted both `proto/` + `dist/proto/` and applied to `proto-v2/`. Detection trigger: reading `src/config/grpc.config.ts`. Lesson already in `long-term-memory/patterns.md` (under "lis-backend-emr-v2 雙 proto 樹").

### **[[VP-15460]]** — `2026-04-28` — redlock CommonJS interop (#88)

Production NestFactory crash at startup: `TypeError: redlock_1.default is not a constructor`. Root cause: `redlock@4` is plain CommonJS (`module.exports = Redlock`, no `.default`); this repo's `tsconfig.json` only sets `allowSyntheticDefaultImports`, not `esModuleInterop`, so `import Redlock from 'redlock'` compiled to `redlock_1.default` (undefined). Should have caught this at code review by recognizing redlock's package age + checking `tsconfig`.

### **[[VP-16337]]** — `2026-04-27 23:38` — **Mistake:** Initially added the new RPC + messages to `src/proto/customer.proto` and `dist/proto/customer.proto`.

**Root cause:** Two parallel proto trees exist in this repo:
- `src/proto/customer.proto` — `package lis;`, used by v1 client connecting to legacy LIS gRPC `192.168.60.6:30276` (`grpcConfig.customer`)
- `src/proto-v2/customer.proto` — `package coresamples_service;`, used by v2 client connecting to coreSamples `10.224.0.199:32100` (`grpcConfigV2.customer`)

`GetClinicIDsByNPINumber` lives only in coreSamples — must go into proto-v2.

**Recovery:** Reverted both `src/proto/` and `dist/proto/` edits, then applied the changes to `src/proto-v2/customer.proto` only (no `dist/proto-v2/` exists, so single file).

**Detection trigger:** Reading `src/config/grpc.config.ts` for endpoint info — saw `getProtoV2Path` and `package: 'coresamples_service'` for the v2 customer client.

### **[[VP-16410]]** — `2026-05-06 11:00` — 在 repo root scripts/ 放 .ts 檔，破壞 nest build dist 結構

- **症狀**：Leo 跑 `npm run start:dev` 報 `Cannot find module '../../prisma2/generated/client2'`
- **誤判**：第一波分析以為是 prisma2 client + postbuild 沒 copy prisma2/ 的 repo 既有 bug，提了 quick fix `cp -r prisma2 dist/`
- **真正根因**：我寫的 `scripts/vp-16410-integration-test.ts` 是放在 repo root `scripts/` 下的 TypeScript file，tsc 預設沒 exclude 這目錄 → 把 `scripts/*.ts` 跟 `src/*.ts` 都 include → 為避免 output 衝突，dist 結構從**扁平**的 `dist/main.js + dist/trans/...` 變成**嵌套**的 `dist/src/main.js + dist/src/trans/... + dist/scripts/...`。`prisma2.service.ts` 用相對路徑 `'../../prisma2/generated/client2'` import，從 `dist/src/trans/` 出發解析 → `dist/prisma2/generated/client2`（不存在）。原本扁平結構從 `dist/trans/` 出發解析 → `LIS-transformer-v2/prisma2/generated/client2`（git tracked，存在）
- **修法**：把 `.ts` script 移到 `~/vp-16410-integration-test.ts.local-backup`，重 build dist 結構就恢復扁平
- **教訓**：
  1. 在 repo root scripts/ 寫 utility 一律用 `.js`（call PrismaClient JS API 即可，不用 ts-node 也能跑）；要寫 TypeScript 就放 `src/` 之外、且加進 `tsconfig.build.json` 的 exclude
  2. 跟 tsc/nest build 路徑解析有關的 bug：先看 `dist/` **頂層結構**（有沒有多/少一層），比 grep import path 更快
  3. user 強調「之前能跑」+ `git diff` 空時，要把搜尋範圍擴到 **untracked .ts 檔可能改變 tsc include scope** 這條軸

---

## Other / uncategorized <a id='other'></a>

### **[[LBS-1487]]**

無。

### **[[VP-16165]]**

_(尚未 execute)_

---

### **[[VP-16424]]**

（無實作層失敗）

**記憶層 failure**：Step 4 呈報時引 VP-16423 STM line 173「kit_delivery_option=BOTH_BLOOD_AND_NON_BLOOD（follow 17412 既有值）」當作 same-practice follow 範例 — 但實際 DB query 17412 與其他 6 provider 全部都是 NO_DELIVERY。Root cause：VP-16423 STM Decisions 區段是早期決策草稿，最終 Leo 在 Step 6 review 時把全部 7 筆改 NO_DELIVERY 但 STM Decisions 沒同步 update（LTM `emr-integration.md` line 436 反而有寫對）。教訓：**引 STM 的決策內容前先用 DB 實際值 cross-check**，特別是時間久的 STM。

### **[[VP-16474]]**

_None._

### **[[VP-16476]]**

_(無 execution failure。Mistakes 在 Retrospective)_

---

---

## Redis / cache / pending list <a id='redis-cache'></a>

### **[[INCIDENT-20260518]]** — `2026-05-18 14:00` — 第一輪 root cause 推錯：Redis emptyDir wipe

**錯誤假設**：Redis sidecar `emptyDir` → pod restart 丟 queue → DB record 變孤兒。
**實際**：Redis 沒被 wipe，job 還在 Redis、worker 沒消費。
**Root cause**：沒先看 BullMQ queue stats (`LLEN waiting`, `LLEN active`, `processedOn`)，直接從 architecture review 推測。
**Preventable**：是。下次先 `redis-cli` 查 queue 實況再下結論。

### **[[INCIDENT-20260518]]** — `2026-05-19` — 建議 `kubectl delete pod` 沒事先警告新 pod 一樣會踩同樣 Redis 坑

雖然新 pod jjk9d 確實踩同樣 Redis NXDOMAIN handler hang，但 Leo 是基於我的建議做的、沒得到預期收益。
**Preventable**：是。對 stateful upstream dependency 的 pod restart 應該預警「新 pod 跟舊 pod 跑同 image 同 ConfigMap，如果問題在 ConfigMap / 環境，restart 沒用」。

---

---

## Deploy / commit / push coordination <a id='deploy-coordination'></a>

### **[[INCIDENT-20260518]]** — `2026-05-19` — 寫 logging 跟 timeout 但沒先說「現在不用 build」

Leo 急著補發、不想 build。我多次 commit + push 沒先問是否需要 deploy。後來 Leo 主動講「現在不用 build」才停下。
**Preventable**：是。緊急 incident 過程中 commit ↔ deploy 是兩個分離決策，要先確認再做。

### **[[VP-15460]]** — `2026-04-28` — Migration not applied automatically

Agent committed migration SQL to repo and assumed release pipeline would `prisma migrate deploy` it. Leo had to remind: "你 sftp_folder_mapping 的改動還沒真的上傳到 database". Then `prisma migrate deploy` failed with P3005 (DB never baselined for prisma migrations) → fell back to `prisma db execute --file <sql>` (raw SQL apply). Then "192.168.60.11:3306 也要 apply" — second DB. Lesson: this repo has two MySQL instances + Prisma is not the migration source-of-truth in prod.

---

## Test / mock / spec <a id='test-mocking'></a>

### **[[VP-16154]]** — `2026-05-11 19:00` — - `event.service.spec.ts` 跟 `meeting-request.service.spec.ts` 用 `new ServiceClass(...)` 直接 instantiate（不走 DI），baseline 上已經缺一個 arg（pre-existing），加 settingTool inject 後 spec compile error 浮現。修法：spec 補 mock arg。



### **[[VP-16612]]** — `2026-05-18` — Pre-existing test broken by env state

`runReminders` test broke during local jest run because Leo's shell `.env` has `platform_type=local`, triggering early-return in `runReminders()`. This wasn't related to my changes but the existing test was env-dependent. Fixed with 1-line `delete process.env.platform_type` in `beforeEach`.

Root cause: VP-16391's test was written assuming `process.env.platform_type` undefined in jest. Works in clean CI/CD, breaks under `.env`-aware shell.

---

## Scope / requirement / PM communication <a id='scope-communication'></a>

### **[[VP-16617]]** — `2026-05-14` — First categorization of 87 dup combos used wrong pattern detection

SQL `COUNT(DISTINCT emr_name)` ignores NULL, so combos with `[NULL, 'PF']` looked like "same emr_name" in audit. Re-wrote categorization with JS `new Set` (treats null as distinct) → revealed 84 combos in "diff emr (one NULL)" pattern previously misclassified as "diff kits".

### **[[VP-16664]]** — `2026-05-18` — Initial date-also-with-TZ assumption

At Step 6 review I included `consult_date: "05/12/2026 PDT"`. Leo corrected to "date does not need TZ; only time-bearing strings do". My reasoning was "dates cross midnight differently in different TZs so date should carry TZ" — technically true but display-copy convention does not write dates with TZ. Lesson: distinguish display-copy convention from technical correctness; the latter does not always require the former.

---

## Tool / cwd / branch / repo confusion <a id='tool-usage'></a>

### **[[VP-15460]]** — [2026-04-27 → 28] Cwd persistence in Bash tool calls

After `cd /Users/hung.l/src/EMR-Backend && gh pr view 156`, subsequent Bash calls without explicit `cd` defaulted to EMR-Backend. Created `bugfix/leo/VP-15460-redlock-import` in the wrong repo, had to clean up. Lesson: always explicit `cd` in cross-repo flows.

---

## Error handling / throw vs log <a id='error-handling'></a>

### **[[VP-16154]]** — `2026-05-11 19:15` — - 第一次 helper 用 `throw new Error('...')` 對 missing header — Leo 要求「沒新 data 不報錯」後改成 try/catch + log.warn + return undefined。



---

## Auth / permission / role <a id='auth-permission'></a>

### **[[VP-16617]]** — `2026-05-14` — kit_delivery_option mis-set on first finalize

Set `kit_delivery_option=NO_DELIVERY` + `kits_options=0` following LTM line 454 and `_apply-vp16424-finalize.ts` template. Both sources were wrong (LTM bug + VP-16424 template propagated the same bug). Caught only after live-applied via cross-check with ParseHL7.java source.

Root cause: LTM had two conflicting statements (mapping table at line 173-176 correct, stub finalize default at line 454 wrong). I followed line 454 without spotting the conflict. Lesson: when LTM has two statements that should agree, verify against authoritative source (Java code here).

---
