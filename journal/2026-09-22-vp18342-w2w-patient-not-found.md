# 2026-09-22 — VP-18342 / VP-18343 / VP-18344: Ways2Wellness "patient_not_found" on the sandbox Partner API

## What Leo asked
"emr API服務 昨天 ways2wellness 他们那个报错 是什麼原因？怎麼處理？" -> then pasted the exact 422 body.
Later: "開票 修法 1 就可以，要能從core-v2 拿資料回來"; "core的proto我们在v1到v2的迁移不打算改…請看看你是不是直接使用 v1 proto";
"開工，要直接讓客戶可以下單"; "開PR, 另外我估計他的意思是以後都用corev1的方式call corev2 rpc, 你試試看行不行(只使用 get 類型的)";
"兩張票都開，core-v2 Address 那張附比對結果"; "merged, 幫我看 staging 部署好之後 W2W 能不能下單";
"他說This project is currently disabled 怎麼會這樣？"; "請根據這個拉proto, v1 proto call v1 rpc, v2 proto call v2 rpc"; "merged, 等deploy好請開始測試".

## Explored / ruled out
- Customer name never appears in any log/DB/Jira (they use the shared sandbox tenant 50687/153895). Dead end until the
  raw error arrived. Ask for the raw error first next time.
- grpcurl (Go) tolerated the drifted proto (garbage, no throw) -> misleading; the emr-v2 Node stack reproduced the
  exact "index out of range: 3603 + 10 > 3603".
- Proto-v2 re-sync as THE fix (built, tested, live-verified) -> reverted after Leo: core wire format is v1's;
  v1 client already existed and fixed the staging->prod routing mix for free.
- Existing v1 getPatient() not reused: it injects mock demographics on empty fields.

## Decisions
- VP-18342 PR #429 (v1 client for GetPatient, 503 on lookup failure); hotfix #431 for the HL7 snake_case shape I broke.
- VP-18343 (core-v2 Address tags) filed with the comparison table; core team shipped #1214 + companions the same day.
- VP-18344 re-scoped: both vendored sets synced from their own upstreams (#432), v1<->v1 / v2<->v2 rule.
- Jenkins multibranch disables `staging` while a PR from it is open -> closed #430 twice to let staging build.

## Evidence trail
Datadog staging 09-21 10:23Z / 13:03Z; staging DB order_intake rows 752-756 (W2W), 773 (control 422), 774 & later
VP18344-VERIFY (201/cancelled); prod in-pod decode check 01:58Z 09-23; core-v2 commits f8c6b287, 751e154a, 4103b443,
0903103b; v1 truth 5ca0a121.
