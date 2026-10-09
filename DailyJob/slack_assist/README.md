# slack_assist — Leo's reply assistant (Phase 1: drafts only)

Runs as a `/loop` inside Leo's interactive Claude Code session (not launchd): every 5 minutes it reads
new Slack mentions / DMs / group DMs and new Outlook mail, classifies them, diagnoses LIS support
questions read-only, and DMs Leo a proposed reply in his own voice (`style.md`). Email replies are
placed in Leo's Outlook Drafts. Nothing is sent to anyone but Leo.

Phase 2 (per class, when Leo says so): replies posted directly. Not enabled.

The claude.ai Slack and Microsoft 365 connectors are session-bound OAuth; this is why the loop lives
in the interactive session. The LangGraph version (see `docs/plans/ticket-lifecycle-graph/DESIGN.md`)
needs a Slack Socket Mode app and a Graph API app registration instead.

Files: `loop_prompt.md` (the per-run instructions), `style.md` (Leo's voice), `ledger.json` /
`log_*.md` / `diffs_*.md` (runtime state, untracked like other DailyJob outputs).

Stop: `/loop` stop in the session. Resume: `/loop 5m` with the prompt again.
