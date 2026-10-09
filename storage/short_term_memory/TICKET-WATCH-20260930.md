---
id: TICKET-WATCH-20260930
type: stm
category: process
status: active
score: 0.0653
base_weight: 0.6
created: 2026-09-30
updated: '2026-10-02'
links: []
relations:
  unblocked_by: []
  blocks: []
  sibling: []
unblock_when: Leo sets REPORT_SMTP_* in .env (Gmail app password); test = the 09:00
  email arrives on the next weekday
tags:
- ticket-watch
- initiator
- daily-report
- automation
- launchd
- bug-watch
- phase-1
- email
summary: 'Workflow inversion: the agent becomes the initiator. Daily 08:00 headless
  run scans Leo''s Jira queue (WORK-LOOP Step 1-2, read-only), writes DailyJob/ticket_watch/report_<date>.md;
  09:00 mailer sends it to leolin84200704@gmail.com. Phase 1 = analysis only; Phase
  2 = execute Routine tickets; Phase 3 = draft PRs. Built on branch feature/leo/ticket-watch-daily-report.'
---

# TICKET-WATCH-20260930 - Work Loop Record

## Ticket Analysis
### [2026-09-30 15:40]
Leo (verbatim): 「我覺得現在的workflow 有可以優化的地方。現在基本上我的工作方式就是我把ticket number 給你然後你自主 -> 這一步是不是可以省略 -> 你綁定我的outlook / jira/ slack mcp, 當有訊息的時候自己判斷/直接/寫報告給我 (基本上就是initiator 從我變成你)」
Then: 「每天要寫一個report (早上九點)到我的leolin84200704@gmail.com 給我看哪些ticket 可以做,做了哪些？哪些需要我決定事情等等。一開始我先確定這個模式可行, 沒問題我們再逐漸放寬限制讓你直接更改code」

Ground truth at start:
- `DailyJob/bug_watch/` is a complete Jira-initiated prototype (2h scan of new bugs, bug-triage skill, whitelisted repush) but `com.lis.bug-watch.plist` was never loaded and no `watch_*.md` report ever existed.
- Loaded launchd jobs: dream, hl7-triage, vibrant-daily-digest, result-fail-watch, consult-recipient. daily-digest runs in an isolated worktree (`~/.lis-daily-digest/main`) and pushes one file to main — the right headless-write pattern.
- Slack / Microsoft 365 MCPs are claude.ai OAuth connectors: "Needs authentication" in `claude mcp list`, unusable from a launchd `claude -p`. bug_watch already switched to Jira REST + API token for this reason.
- Mail.app has zero accounts; no msmtp; postfix has no relay → any email transport needs credentials Leo must create.
- Jira REST `search/jql` with Leo's token: queue (`assignee = currentUser() AND statusCategory != Done`) is >50 issues incl. QH- QA twins; 3 new unassigned bugs in 24h; 19 of his tickets updated in 24h.

## Approaches Considered
- Single 08:30 job that analyzes AND emails — rejected: a claude failure would mean no email, and "no email" is indistinguishable from "nothing happened" (dream's silent 3-night abort, Aug 2026).
- Chosen: two launchd jobs. 08:00 `run_ticket_watch.sh` (claude -p, read-only prompt) → report file; 09:00 `send_report.py` (plain python SMTP, no LLM) sends the file or an explicit "沒有產生報告" alert. Every early exit in the runner also writes a failure report.
- Phase ladder in README: 1 analysis-only (now) → 2 execute Routine + Class A repush → 3 draft PRs. Widening = prompt constraints block + `--allowedTools`, via PR.
- Email transport: Gmail app password on leolin84200704@gmail.com sending to itself (simplest, no company tenant involved); any SMTP relay works with the same REPORT_* vars.

## Decisions Made
- Slack / Outlook triggers deferred to Phase 2+ (need bot / Graph tokens; Outlook noisiest → sender allowlist of vendors).
- Headless job reads from the live main checkout (like hl7/result_fail jobs) but Phase 1 writes only the untracked report file; `TICKETWATCH_AGENT_ROOT` override exists for worktree trials.
- Reports stay untracked, same as every other DailyJob folder.
- All hard-coded strings in the runner/mailer are English (validate-repo-language hook blocks CJK in non-.md staged files); the zh-TW content comes only from the prompt output. Summary extraction reads the line under `## Summary` instead of matching CJK.
- Trial runs were executed by me before Leo saw the PR: read-only by construction, and a sample report is the thing he asked to judge the model on.

## Code Changes
Branch `feature/leo/ticket-watch-daily-report` (worktree `.git-worktrees/ticket-watch`):
- `DailyJob/ticket_watch/{watch_prompt.md, run_ticket_watch.sh, send_report.py, run_send_report.sh, README.md, com.lis.ticket-watch.plist, com.lis.ticket-report-mail.plist}`
- `.env.example` (+REPORT_SMTP_*), `CLAUDE.md` (headless model list + TICKETWATCH_MODEL)
- PR #52 https://github.com/leolin84200704/vibrant-america-working-agent/pull/52 (head 5d7bac1, one commit). Not merged; worktree `.git-worktrees/ticket-watch` kept (has a gitignored `.env -> ../../.env` symlink for trials).

## Test Results
- plutil -lint both plists OK; bash -n / py_compile OK; placeholder substitution leaves 0 `{{`.
- Mailer dry run with a missing report → correct alert subject/body.
- Jira pre-flight `/rest/api/3/myself` 200; all three JQLs return.
- Trial run 2 (after the 401 fix): 2026-09-30 16:11-16:23 (12 min), queue 107 issues (18 VP/LBS + 89 QH; 84 QH are orphan twins), 3 new unassigned bugs, DB up. Report `DailyJob/ticket_watch/report_2026-09-30.md` (copied into the main checkout, untracked): 可以做 2 / 待決定 6 / 等別人 8 / 未分析 4. Afterwards: agent repo and all work repos had no new tracked changes; 0 credential strings in the report. Mailer dry run on the real report yields subject `[LIS Agent] Ticket Watch 2026-09-30 — 可以做: 2 | ...`.

## User Feedback
### [2026-09-30 17:05]
Leo: 「merged」(PR #52, merge commit 81da828). Main checkout fast-forwarded; worktree `.git-worktrees/ticket-watch` and local branch removed (remote branch left in place). Both plists copied to ~/Library/LaunchAgents and loaded (`launchctl list` shows com.lis.ticket-watch and com.lis.ticket-report-mail, exit 0). First scheduled run: 2026-10-01 08:00 / 09:00. `REPORT_SMTP_*` still unset in .env, so the 09:00 mailer will exit 2 with a macOS notification until Leo adds the Gmail app password; the 08:00 report will still be written to DailyJob/ticket_watch/.
## Failures
### [2026-09-30 16:10]
Trial run 1: both claude -p attempts died with `401 Authentication Failed`. Cause: the runner's Jira pre-flight did `set -a; source .env`, exporting the empty `ANTHROPIC_API_KEY=` / `ANTHROPIC_BASE_URL=` lines into the claude process, which then bypassed the keychain login. Fix: read only the three JIRA_* values with grep/cut, export nothing. The failure-report path worked as designed (report file + notification produced).
## Retrospective
## Lessons Learned

### [2026-10-02 dream] First two scheduled days: both RUN FAILED (no network), mailer exit 2 (SMTP unset)
- 10-01 and 10-02 `run_ticket_watch.sh` aborted "Network unavailable after 60s" (api.anthropic.com unreachable from this Mac most of both days — dream deferred 5 times for the same reason) and wrote the failure report (`report_2026-10-01.md`, `report_2026-10-02.md`); `send_report.py` exited 2 both mornings ("email not configured"). The alert-on-silence path works; Leo still has to set `REPORT_SMTP_USER/PASSWORD` for anyone to receive it. `unblock_when` unchanged.
