---
date: 2026-10-26
ticket: QH-CLOSEOUT-20261026
type: journal
tags: [qh, qa-twin, closeout, dev-complete, done, process, leo-rule]
related: [VP-18449, VP-18450, VP-18464, VP-18481, VP-18482, VP-18673, VP-18796, VP-18798, VP-18799, VP-18800, VP-18801, VP-18802, VP-18889, VP-18960, VP-19006, VP-19007, VP-19009, VP-19011, VP-19019, VP-19023, VP-19024]
distilled: false
---

# QH twin closeout sweep: 21 Dev Complete tickets, 13 closed, 6 not ready, 2 ownership questions

## Leo's new rule (2026-10-26)
"Dev Complete 後都要看看有沒有 related 的 QH ticket，有的話要一併做了然後填完後 done ticket。"
Mechanics established this session and proposed in CLAUDE.md via PR #66 (personal repo):
- QH twin = issuelink type "Test" (VP `is tested by` QH), auto-created by Automation for Jira with an empty description.
- Fill = one English comment "QA verification passed on {date} for VP-xxxx" with Implementation / Verification / Residual sections, every bullet carrying PR, merge commit, comment id or date (format borrowed from Ethan's QH-7314 and Yekai's QH-6706).
- QH transition 31 = Done. `fields.assignee` is NOT on the QH transition screen (400); set assignee with editJiraIssue separately.
- VP transition 15 = Dev Complete -> Done. One-line VP comment pointing at the QH comment id, then transition.
- Done criteria unchanged: code in prod + verified. Missing evidence = report, do not close.
- Historically nobody filled QH twins (Leo's and QA's Done QH all carry only the Automation "linked issue resolved" comment). This sweep is the first time they carry evidence.

## What was done
Five opus subagents drafted evidence per ticket family from STM + Jira dumps + `gh pr view`; I reviewed, posted as Leo via Atlassian MCP.

Closed (QH comment id / VP comment id):
| VP | QH | QH comment | VP comment |
|---|---|---|---|
| VP-18449 | QH-7307 | 197846 | 197877 |
| VP-18673 | QH-7487 | 197847 | 197878 |
| VP-18796 | QH-7667 | 197848 | 197879 |
| VP-18798 | QH-7669 | 197849 | 197881 |
| VP-18799 | QH-7670 | 197850 | 197882 |
| VP-18800 | QH-7671 | 197851 | 197883 |
| VP-18801 | QH-7672 | 197852 | 197884 |
| VP-18889 | QH-7781 | 197853 | 197885 |
| VP-18960 | QH-7860 | 197854 | 197886 |
| VP-19007 | QH-7925 | 197855 | 197887 |
| VP-19011 | QH-7934 | 197859 | 197888 |
| VP-19019 | QH-7954 | 197860 | 197889 |
| VP-19023 | QH-7960 | 197861 | 197890 |
QH-7667/7669/7670/7671/7672 were unassigned; assigned to Leo.

## Not closed, decision needed
- VP-18450 / QH-7308: dead `coreSampleV2Url` block removed by LIS-transformer #782 was reintroduced by the #792 merge; still on main 73bf420 (src/trans/trans.grpc.options.ts ~171-182). Option: tiny re-removal PR, or accept as residual with an owner ticket.
- VP-18464 / QH-7322: description steps 1-3 (caller list, migration tickets, cutoff) not done; 30-day window closes 2026-11-05/06. Datadog last 15 d: 0 external callers (2 own probes). On-prem half had evidence since 10-05 (Ray not needed). appserver04 capture loop unverified since 10-08.
- VP-18802 / QH-7673: prod read-only A/B 27/28; `GET /storage/racks/suggestions` 500 on trans prod because `DATABASE_URL_VA_INFO_MASTER` is missing from lis-trans-config / lis-trans-secret / deployment env (re-checked 10-26). Option (a) add the key (prod config change, lis-prod-change-gate) and re-run; (b) accept as VP-18803 precondition.
- VP-19006 / QH-7924: AC4 Slack post never observed (staging SENTRY_DSN unset, prod 0 rejects); AC6 only an in-repo addendum docs/hl7-order-spec-kit-delivery.md + Jira 193465, standard partner spec not updated; no real ZKD order yet.
- VP-19009 / QH-7932: code in prod (#732 6acbfdb), prod read-only expansion of 65 series OK, but per-occurrence edit/cancel never ran in prod (FE VP-19010 does not send scope yet); THIS_AND_FUTURE and AC6 availability have unit tests only. Decision: accept staging evidence, or run a prod test series.
- VP-19024 / QH-7961: code shipped and prod-smoked (not design-only; STM index line stale). Scope change unrecorded on ticket (practice admin gets suspend + withdraw; approve/reject stay Vibrant-internal, Leo 10-23). AC2 outsider-reject, AC3 own-status read, AC4 acting user not itemized in STM.

## Ownership question
QH-7340 (VP-18482) is assigned to Yuteng Fu and QH-7339 (VP-18481) to Michael Kingsley. Both VP tickets judged READY (drafts in scratchpad out-A1.md). Per the standing "do not transition other people's tickets" rule I did not comment or close them; VP-18481/18482 stay Dev Complete until Leo says close, reassign, or leave to QA.

## Findings worth keeping
- STM `_index.md` lines were stale for VP-19019 ("release pending" but #505 merged 10-24), VP-18960 ("shadow" but enforce on since 10-21) and VP-19024 ("design pending" but shipped). Index summaries lag the STM body; verify before quoting.
- `DailyJob/lis_sample_route_removal/routes.json` puts kits (VP-18482, deadline 11-05, 30-day rule) and retrieval (VP-18796, 30-day soak to 11-13) in batch 1 (deadline 10-30, 14-day rule). The job could open removal PRs early; needs a config fix.
- VP-18796 results staging mirror waiver (Yekai DM 10-19) was only in STM; now recorded on QH-7667.
- Not visible to daily hl7_fail triage: `vendor_mismatch` class (VP-18960). Needs a PR.
- VP-18481 prod consumer cutover has no owner ticket; design note / cutover runbook only in drafts/, not Confluence.
- Staging sample 2463379 carries TNP '-45' twice from the 10-14 VP-18801 smoke test; cleanup undecided.
- VP-18673 PDF download path still uses static VIBRANT_API_TOKEN; no ticket.

## Friction
- transitionJiraIssue `fields.assignee` fails on QH (no screen); use editJiraIssue.
- JQL evidence view for 21 issues is ~480 KB; jq over the saved file is the only workable path.
