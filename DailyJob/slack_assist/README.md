# slack_assist — Leo's reply assistant (Phase 1: drafts only, headless)

Runs from launchd (`com.lis.slack-assist`) every 20 minutes, Mon-Fri 09:00-18:00, on Leo's Mac.
Each run is a deterministic Python poll (`assist_poll.py`) over new Slack mentions / DMs / group DMs
and new Outlook mail. **Nothing new = no model call.** When there are candidates, ONE `claude -p`
worker (`worker_prompt.md`, `--json-schema`, read-only tools) classifies, diagnoses and drafts; the
script then performs the only two outbound actions of this phase: a Slack DM to Leo with the
diagnosis + proposed reply, and an Outlook *draft* in Leo's Drafts folder. Nothing is sent to anyone
but Leo. Phase 2 (direct replies per class) is a separate change.

The claude.ai Slack / Microsoft 365 connectors are session-bound OAuth and do not exist headless, so
the script talks to the Slack Web API and Microsoft Graph with tokens Leo creates once.

## One-time setup (Leo)

1. **Slack user token** (acts as Leo, same reach as the connector): api.slack.com/apps -> Create App
   (from scratch, workspace Vibrant) -> OAuth & Permissions -> *User Token Scopes*:
   `search:read`, `channels:history`, `groups:history`, `im:history`, `mpim:history`, `im:read`,
   `mpim:read`, `users:read`, `chat:write` -> Install to Workspace -> copy the `xoxp-` token into the
   agent root `.env` as `SLACK_USER_TOKEN=`.
2. **Outlook (Graph, delegated)**: `~/.venvs/slack-assist/bin/python DailyJob/slack_assist/graph_login.py`,
   follow the device-code prompt once. It stores a refreshable token cache at
   `~/.config/support-assist/msal_cache.json` (0600). If the tenant refuses the public client, IT must
   register an app; then set `ASSIST_GRAPH_CLIENT_ID` in `.env` and rerun.
3. **venv**: `python3.13 -m venv ~/.venvs/slack-assist && ~/.venvs/slack-assist/bin/pip install -r DailyJob/slack_assist/requirements.txt`
4. **launchd** (after this branch is on main): `cp DailyJob/slack_assist/com.lis.slack-assist.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.lis.slack-assist.plist`
5. Manual run any time: `DailyJob/slack_assist/run_assist.sh --force` (ignores the time window).

Optional `.env` keys: `ASSIST_MODEL` (default `fable`; `sonnet` is 5x cheaper for drafting-only days),
`ASSIST_MAX_TURNS` (default 25), `ASSIST_MAIL_ME` (default hung.l@zymebalanz.com).

## Cost model

- Empty poll: 2-4 HTTP calls, no LLM. 27 slots/day x 5 days = 135 polls/week at zero model cost.
- Run with candidates: one `claude -p` under the machine's claude.ai login (plan seat, not API billing);
  the `list-cost=$` in the log is the list-price equivalent for reference only.
- Worker budget: 25 tool calls per batch, read-only.

## Files

- `assist_poll.py` — poll, context fetch, worker call, DM + Outlook draft, ledger, log
- `worker_prompt.md` — the one LLM call's instructions and output contract
- `style.md` — Leo's Slack voice (7 rules + worked example); never auto-edited
- `graph_login.py` — one-time device-code login for Graph
- `run_assist.sh`, `com.lis.slack-assist.plist` — launchd entry (Mon-Fri 09:00-17:40, every 20 min)
- `ledger.json`, `log_*.md`, `launchd_*.log` — runtime state, untracked

## Diff learning (unchanged intent)

Leo sends the reply himself. The draft and the DM timestamp are in `ledger.json`; comparing them with
what Leo actually sent is the signal for style changes, which are proposed in `diffs_*.md` and never
auto-applied to `style.md`.
