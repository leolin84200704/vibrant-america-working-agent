# AI-Native Bug Watch — scheduled run

You are running headless as the scheduled bug-watch job. Look back **{{LOOKBACK_HOURS}} hours** for newly created bug tickets, triage each one, and write the digest to `{{REPORT_FILE}}`. The runner already verified prod DB reachability before starting this run (it skips entirely when the VPN is down).

## Step 1 — Fetch new tickets (Jira REST, not MCP)

Credentials: `JIRA_SERVER`, `JIRA_EMAIL`, `JIRA_API_TOKEN` from `.env` in the agent root (same as `scripts/reconcile-jira.py` — Basic auth, base64 of `email:token`).

Query `/rest/api/3/search/jql` (the old `/rest/api/2/search` returns HTTP 410 Gone — verified 2026-07-06) with JQL:

```
((project = VP AND issuetype = Bug) OR project = LBS) AND created >= "-{{LOOKBACK_HOURS}}h" ORDER BY created ASC
```

Fields: `summary,status,priority,assignee,description,created,reporter`. If the request fails, write the report with a loud **JIRA UNREACHABLE** header and stop — never report "no new bugs" on a failed query.

Tickets already Done/Closed at fetch time get a one-line entry in the digest (id, summary, resolution) — do not triage them.

**Dedupe across runs**: grep earlier `DailyJob/bug_watch/watch_*.md` for each ticket id. If a ticket was already triaged and its Jira status/description is unchanged, list it under "previously triaged" with one line instead of re-running the full flow.

## Step 2 — Triage each ticket

Read `.claude/skills/bug-triage/SKILL.md` and follow its flow for each ticket, under these **watch-mode constraints**:

- **Allowed without a human**: read-only diagnosis (Jira, DB queries when DB is up, SFTP listings), and the whitelisted repush action (Class A: `generateResultHl7` via gRPC, with the skill's pre-checks and mandatory 100% post-verify).
- **NOT in watch mode**: code changes, branches, PRs (Class C/D stops after root-cause diagnosis — flag `interactive follow-up: /bug-triage {id}` in the digest); any prod UPDATE/DELETE/INSERT; posting Jira comments or Slack messages (draft them into the digest only).
- If the DB becomes unreachable mid-run (VPN can drop at any time), mark the affected diagnoses **BLOCKED — VPN down** (empty result ≠ no failures); never present a failed query as "no records".
- Per-ticket budget: keep diagnosis focused; if a ticket needs deep code archaeology, classify it, note the entry points, and flag it for interactive follow-up rather than burning the whole run on one ticket.
- Create an STM file (`storage/short_term_memory/{ticket_id}.md`) only for tickets where you executed an action (e.g. a repush); digest-only tickets do not get STM shells.

## Step 3 — Digest report (zh-TW)

Write `{{REPORT_FILE}}`:

```markdown
# Bug Watch — {date} ({{LOOKBACK_HOURS}}h lookback, DB {{DB_STATUS}})

## Summary
- Total new: X | auto-resolved: X | awaiting approval: X | interactive follow-up: X | blocked: X

## {TICKET-ID} — {summary}
- 分類: A/B/C/D/E ｜ 診斷鏈: ...
- 已執行: ...（post-verify 結果）/ 無
- 待 Leo: ...（待批准 SQL / interactive follow-up / 起草的 comment）
```

Rules: 使用繁體中文寫報告；每張 ticket 的起草 comment（英文）放在該 ticket 段落內；不需要 user confirmation，直接執行到報告寫完為止。
