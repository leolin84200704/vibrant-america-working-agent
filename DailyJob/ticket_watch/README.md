# Ticket Watch — the agent as initiator

Every morning the agent looks at Leo's Jira queue on its own, does the retrieve-and-analyze
steps of the work loop (WORK-LOOP Step 1–2), and emails one report: which tickets it could
do, what it did, and what needs Leo's decision. Leo stops being the dispatcher; he becomes
the reviewer of a report that arrives at 09:00.

Leo's framing (2026-09-30): "一開始我先確定這個模式可行, 沒問題我們再逐漸放寬限制讓你直接更改code".

## Phases

| Phase | What the job may do | Gate to the next phase |
|-------|---------------------|------------------------|
| **1 (current)** | Read Jira, memory, repos, prod DB (SELECT). Write ONE report file. Nothing else. | Leo agrees the picks and plans are right for a couple of weeks |
| 2 | Execute **Routine** tickets end to end (config/integration rows that mirror a precedent), with 100% post-verify, and the Class A result repush. Draft PRs for nothing yet. | Zero wrong executions over the trial |
| 3 | Code-change tickets → branch + tests + draft PR (WORK-LOOP Step 5–6) for Leo to review. Still no merge, no prod write outside the whitelist. | — |

Widening a phase means editing `watch_prompt.md` (the constraints block) and the
`--allowedTools` list in `run_ticket_watch.sh`, through a PR.

## Two jobs, on purpose

- `com.lis.ticket-watch` — **08:00**, `run_ticket_watch.sh` → `claude -p watch_prompt.md`
  → `report_YYYY-MM-DD.md`. Dynamic lookback (since the last report, +1h, clamped 24–168h).
- `com.lis.ticket-report-mail` — **09:00**, `run_send_report.sh` → `send_report.py`.
  Plain shell + python, no LLM. Sends the report, or an explicit "沒有產生報告" alert when
  the 08:00 run left nothing (waits up to 15 min first). A stalled job must produce an
  email that says so — "no email" being indistinguishable from "nothing happened" is how
  the dream pipeline died silently for three nights in August.

Every early exit in the 08:00 runner (no network, Jira unreachable, claude failed) writes a
failure report too, so the 09:00 mail always has something truthful to say.

## Install

```bash
cp DailyJob/ticket_watch/com.lis.ticket-watch.plist DailyJob/ticket_watch/com.lis.ticket-report-mail.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.lis.ticket-watch.plist
launchctl load ~/Library/LaunchAgents/com.lis.ticket-report-mail.plist
launchctl list | grep com.lis.ticket
```

Run once by hand: `bash DailyJob/ticket_watch/run_ticket_watch.sh` then
`python3 DailyJob/ticket_watch/send_report.py --wait-minutes 0` (add `--dry-run` to print
instead of sending).

## Email setup (one-time, Leo)

The report goes to `leolin84200704@gmail.com`. Mail.app on this machine has no accounts and
the Microsoft 365 / Slack MCP connectors are claude.ai OAuth sessions that a launchd job
cannot use, so the mailer speaks SMTP directly. Simplest transport is Gmail sending to
itself with an app password:

1. Google Account → Security → 2-Step Verification (must be on) → App passwords → create one
   named `lis-agent`.
2. Add to `.env` in the agent root (never committed):
   ```
   REPORT_SMTP_HOST=smtp.gmail.com
   REPORT_SMTP_PORT=587
   REPORT_SMTP_USER=leolin84200704@gmail.com
   REPORT_SMTP_PASSWORD=<16-char app password>
   REPORT_EMAIL_TO=leolin84200704@gmail.com
   ```
3. `python3 DailyJob/ticket_watch/send_report.py --wait-minutes 0` and check the inbox.

Any other SMTP relay (e.g. the work tenant, if SMTP AUTH is enabled there) works with the
same five variables. Until they are set, the mailer exits 2 and posts a macOS notification
"email not configured".

## Files

- `watch_prompt.md` — the analysis prompt; the Phase constraints live at its bottom
- `run_ticket_watch.sh` — 08:00 runner (pre-flights, lookback, retries, failure report)
- `send_report.py`, `run_send_report.sh` — 09:00 mailer
- `report_YYYY-MM-DD.md`, `run_YYYY-MM-DD.log`, `launchd_*.log` — outputs, untracked like the
  other DailyJob folders

## Scope notes

- Queue = `assignee = currentUser()` with Leo's Jira token, plus unassigned new VP bugs / LBS
  tickets (the same population bug_watch was built for; that job's plist was never loaded).
- Slack and Outlook as triggers are Phase 2+ material and need their own tokens; see the
  2026-09-30 STM `TICKET-WATCH-20260930` for the plan.
