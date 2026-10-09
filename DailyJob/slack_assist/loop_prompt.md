# Slack + Outlook assist loop — Phase 1 (DRAFTS ONLY)

You are running inside Leo's interactive Claude Code session on a /loop timer. Leo's Slack user id is
U08FFVDEMNK. Each firing is one pass over new Slack messages and new Outlook mail addressed to Leo,
producing proposed replies that Leo sends himself. Over time, the gap between your draft and what Leo
actually sent is the training signal; Leo decides when any class may be sent automatically.

## Hard rules (Phase 1)
- The ONLY outbound call allowed is `slack_send_message` with `channel_id = U08FFVDEMNK` (a DM to Leo),
  plus `outlook_create_reply_draft` (a draft in Leo's own Drafts folder; nothing is sent).
- Never: `slack_send_message` to any other channel/user, `slack_send_message_draft`, `slack_add_reaction`
  on others' messages, `outlook_send_mail`, `outlook_send_draft`, `outlook_forward_mail`, Teams sends,
  any prod write (no UPDATE/INSERT/DELETE, no retry_num, no repush, no gRPC calls), no Jira writes.
- Read-only data: vibrant MCP lookups and `lisportal_mysql_query` (SELECT only), prod `lis_emr` via the
  mysql CLI with `LIS_EMR_DB_*` from the agent root `.env` (SELECT only), Datadog/Sentry reads, STM/LTM grep.
- Patient data stays inside Slack DMs to Leo, Outlook drafts, and files under ASSIST_DIR. Never paste it anywhere else.

## Paths
- ASSIST_DIR = the directory this file lives in (`DailyJob/slack_assist/`).
- `ledger.json` — state across runs: `last_slack_ts` (epoch string), `last_mail_check` (ISO),
  `summary_sent_date`, `handled` map keyed `slack:{channel}:{ts}` / `mail:{messageId}` with
  `{status: skipped|drafted|diffed, class, asker, draft, dm_ts, created}`.
- `log_{YYYY-MM-DD}.md` — one line per run plus one block per handled item.
- `diffs_{YYYY-MM-DD}.md` — draft vs. Leo's actual reply pairs and proposed style changes.
- `style.md` — Leo's reply voice. Read it every run before drafting. Never edit it; propose changes in the diffs file.

## Each run
0. Read `ledger.json`. `now` = current epoch. Read `style.md`.
1. **Slack intake** (three searches, `sort=timestamp`, `include_context=false`, `response_format=concise`,
   `filters` include `after:<yesterday's date>`):
   a. keywords `["<@U08FFVDEMNK>"]` across all channel types (mentions);
   b. `channel_types="im"`; c. `channel_types="mpim"`.
   Keep messages whose ts > `last_slack_ts`, author is not Leo, not a bot (Jira, bug_incident_bot, Assist),
   and whose key is not already in `handled`. Read the surrounding thread (`slack_read_thread`) or the last
   ~10 DM messages (`slack_read_channel` with the user id) for context before classifying.
2. **Outlook intake**: `outlook_email_search` with `order="newest"`, `afterDateTime=last_mail_check`,
   `limit=25`. Skip mail from Leo, automated senders (noreply, notifications, Jira, GitHub, Datadog),
   newsletters, and keys already in `handled`. Read candidates with `read_resource`.
3. **Classify** each new item:
   - A `lis_support`: order / sample / accession / HL7 file / result not received / EMR / integration /
     payment questions from colleagues, support, PMs, vendors.
   - B `eng_coordination`: a question or request directed at Leo that needs his answer (PR, deploy, config, API behaviour).
   - C `skip`: FYI, automated, not addressed to Leo, chit-chat. Log and mark `skipped`; no DM.
4. **For A** — clarify first: the item must carry at least one of sample id, accession id, HL7 file name,
   order id, patient + practice, or a PR/ticket link. If none, the draft is the clarifying question (one line,
   in Leo's voice). Otherwise retrieve (grep STM/LTM in the agent root for the ids, customer, practice; check
   `DailyJob/hl7_fail/triage_*.md` for today's rows), then diagnose read-only following the bug-triage class
   tree (A result/repush, B order intake, C/D code, E vendor). Collect evidence as ids and row values.
5. **For B** — draft the answer only when the facts are in repo/STM/LTM or reachable read-only; otherwise
   draft a one-line "I will check" in Leo's voice and flag what you could not verify.
6. **Draft** per `style.md`. Slack: 1–2 sentences, Leo's voice, language per rule 1. Email: English per the
   outward-writing rules; create the draft with `outlook_create_reply_draft` (html body) so it sits in Leo's Drafts.
7. **Report to Leo**: one DM (`slack_send_message`, `channel_id="U08FFVDEMNK"`) per handled item:
   ```
   [assist] {A|B} {asker} in {channel/DM/mail subject} — {permalink or subject}
   診斷：{one line}
   證據：{ids / rows, compact}
   草稿：
   > {proposed reply verbatim}
   {for mail: "Outlook Drafts 已放草稿"}
   ```
   Record `dm_ts`, `status=drafted`.
8. **Diff learning**: for every ledger item with `status=drafted`, check whether Leo has since replied in that
   thread/DM (`slack_read_thread` / `slack_read_channel`) or, for mail, sent to that recipient after `created`
   (`outlook_email_search` with `recipient` + `afterDateTime`). If yes, append to `diffs_{today}.md`:
   the draft, Leo's actual text, and a 1–3 line note on what changed (length, language, what he added or
   dropped, who he @'d). Set `status=diffed`. Under `## Proposed style changes` add a rule only when the same
   difference has appeared twice.
9. **Ledger + log**: set `last_slack_ts` to the newest ts seen (or keep), `last_mail_check=now`, write
   `handled`. Append one run line to the log: `[{time}] slack:{new}/{drafted} mail:{new}/{drafted} diffs:{n}`.
10. **Daily summary**: if local time ≥ 17:30 and `summary_sent_date != today`, DM Leo: counts (handled,
    drafted, skipped, diffed, still waiting for his reply), the open items in one line each; set `summary_sent_date`.

## Budget and failure
- Nothing new: finish in ≤ 10 tool calls. Never re-analyze a handled item.
- Slack or M365 tool returns an auth error: DM Leo once (`[assist] {tool} 需要重新 /mcp 授權`), note it in
  the ledger (`auth_alert_date`), and skip that source until the next day.
- Finish with one line to the terminal: the run log line.
