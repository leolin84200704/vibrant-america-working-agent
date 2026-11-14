---
id: 2026-11-14-slack-livecheck-plan-approval
type: journal
date: 2026-11-14
tickets: [SLACK-LIVECHECK]
tags: [daemon, live-check, plan-approval]
distilled: false
---
# SLACK-LIVECHECK: plan approval path live check

Trigger: Leo asked over Telegram for a plan only (run `echo live-check` locally), approved=false.
His next message "做完跟我說" was written before the plan reached him; the daemon flagged the timing,
so it was answered as not-yet-approved and the plan stayed pending. His following "ok" approved it.
The command ran once and printed `live-check`. The daemon then sent the Steps 5-7/9 closeout; since
the plan was an operation and not a code change, no worktree, branch or PR was created.

Lesson: an approval that predates the proposal it would approve is not an approval. Keep the plan field
filled while it waits so the daemon state still has something for the later "ok" to act on.
