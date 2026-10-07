---
id: HL7-TRIAGE-LANGGRAPH
type: stm
category: process
status: active
score: 0.00
base_weight: 0.6
created: 2026-10-07
updated: 2026-10-07
links: []
relations:
  unblocked_by: []
  blocks: []
  sibling: [HL7FAIL-20260729-PLESSEN]
unblock_when: ""
tags: [hl7-triage, langgraph, dailyjob, automation]
summary: "LangGraph port of the hl7_file_input daily triage: deterministic nodes + one claude -p narrative node + email; parallel-run phase"
---
# HL7-TRIAGE-LANGGRAPH - Work Loop Record

## Ticket Analysis
### [2026-10-07 10:30]
Leo (no Jira ticket): wants the HL7 triage as a LangGraph graph that mails him the report, running on his own
machine with the regular Claude Code login, not an API key.

Findings before building:
- `com.lis.hl7-triage` runs `run_triage.sh` at 04:00 -> `claude -p triage_prompt.md` (30 turns). It never mailed;
  reports 10-01..10-07 were all BLOCKED (VPN down overnight) and nobody was told.
- `hl7_triage_runner.py` already had the deterministic parts (pymysql, JWT, pricing APIs) but was not scheduled.
- `ticket_watch/send_report.py` is the reusable SMTP mailer; REPORT_SMTP_* are NOT set in .env, so every mailer
  exits 2 "email not configured". Leo must create a Gmail app password (ticket_watch/README.md) before any mail goes out.
- `.env` carries ANTHROPIC_API_KEY/BASE_URL for a z.ai proxy; they must never reach `claude -p` (breaks login).
- `claude auth status`: authMethod claude.ai (Vibrant org), no API key. `claude -p --output-format json --json-schema`
  returns `structured_output` validated; stdin prompt works; from an empty cwd the context is ~8.6k tokens vs ~36k
  inside the agent repo.
- Leo's `~/src/langgraph-study` uses langgraph 1.2 + ChatAnthropic (API key). Our node uses subprocess `claude -p` instead.
- Live schema confirmed: hl7_file_input has customer_not_found / last_error / error_detail; quarantined_orders carries
  provider_npi, patient, order_id, raw HL7 (OBR codes) and matched_integration_id. FollowThatPatient puts the VA
  customer_id (not an NPI) in ORC.12 (row 7266: 43262).

## Approaches Considered
- A: langchain-anthropic ChatAnthropic -> needs API key / `ant auth login` Console OAuth (separate billing). Rejected per Leo.
- B: LangGraph locally, LLM node = subprocess `claude -p` under the claude.ai login. Chosen.
- Step 0 independent of the graph: mail the existing prompt-driven report from run_triage.sh (success, BLOCKED, retry-fail).

## Decisions Made
- Graph is read-only against prod. Type B payment/order recovery (prompt Step 4, prod writes) is NOT ported; rows are listed as pending manual recovery.
- Classification gains a CNF bucket (customer_not_found) in front of the old Type C.
- Sibling OBR codes from the quarantined raw HL7 are looked up next to the flagged code (the 09-30 human report did this).
- Parallel-run phase: `run_graph.sh` (PARALLEL=1) writes `DailyJob/hl7_fail/graph_out/` and does not mail; launchd stays on run_triage.sh until Leo switches.
- Secrets: LIS_EMR_DB_* appended to local .env (gitignored); pricing token falls back to EMR-Backend orderApi.yaml.

## Code Changes
Branch `feature/leo/hl7-triage-langgraph` (worktree `.git-worktrees/hl7-triage-graph`), venv `~/.venvs/hl7-triage-graph` (py3.13, langgraph 1.2.14):
- `DailyJob/hl7_fail/graph/hl7_triage_graph/` (config, state, db, resolve, pricing, llm, report, nodes, graph, __main__) + README + requirements
- `DailyJob/hl7_fail/send_triage_mail.py` (shared transport with ticket_watch), `run_graph.sh`
- `run_triage.sh`: `send_mail()` on success / BLOCKED / retry failure

## Test Results
### [2026-10-07 11:10]
- `--no-llm --dry-run` live: 4 rows (A=3 VAREQUISTION471 x3, CNF=1), 3/4 resolved, catalog 303 pp / 6267 bundles, 6.5s.
  Facts match the 09-30 human report (NPI 1750375671 -> integration cmkzxxmsxa9c43540e4e46f0e, 471 missing from catalog).
- `--dry-run` with LLM: 66s total, narrative grounded (no invented ids), flagged that 462/463 were not looked up -> fixed by sibling-OBR lookup.
- Mailer dry runs: BLOCKED / tally / NO REPORT subjects correct; real send exits 2 (not configured) as expected.

## User Feedback
## Failures
## Retrospective
## Lessons Learned
- `claude -p` is a legitimate LangGraph LLM node when the only credential is a claude.ai login: stdin prompt, `--json-schema`, scrubbed env, empty cwd.
