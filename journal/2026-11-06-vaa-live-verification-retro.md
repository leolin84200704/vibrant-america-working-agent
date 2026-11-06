---
date: 2026-11-06
tickets: [VP-17466, VP-17756, VP-19013, VP-19142]
tags: [vibrant-america-auto, daemon, verification, retrospective, process, headless, mcp]
---
# Retro: why daemon changes kept shipping green and not working (2026-11-03..06)

Leo asked, after the Slack-draft fix (#46) changed nothing, why the same kind of thing keeps happening
on vibrant-america-auto. Five PRs in four days: each passed its unit tests, each was reported as done,
each failed in use for the same reason.

| PR | the assumption the code and its test encoded | what the environment did |
|---|---|---|
| #46 Slack drafts | tool names are `mcp__plugin_slack_slack__*`, as the interactive session lists them | `claude -p` suppresses the synced plugin as a duplicate of the claude.ai Slack connector ("Lazy dedup" in the MCP debug log) and serves `mcp__claude_ai_Slack__*`, which stayed denied. Found by `claude -p --debug=mcp` after Leo reported it twice |
| #40 token rotation | a PR based on an open PR retargets to main when the base merges | merged two minutes after the base, it landed in the feature branch; main never got the commit until #41 |
| #44 install | `launchd/install.sh` is safe at any time | the restart killed the run on Leo's "ok" for VP-17466 19 s after it arrived; the ok was lost, recovered by hand with the `reply` CLI |
| #39 session rotation | the handoff entry is the newest note | stamped with the rotation time, it outranked an STM entry Leo's interactive session wrote later; the fresh VP-19013 session repeated "E2E not run" |
| Telegram sends | `sendMessage` succeeds | a DNS failure dropped the VP-19142 reply; no retry, no queue |

Root cause, one sentence: the behaviour lived in the environment (headless tool surface, GitHub, launchd,
Telegram) and I verified it against fakes (`ScriptedRun`, `FakeJira`, `FakeListener`) that encoded my
own belief, then reported "tests pass" as if it were "the daemon does it". The factory hot lesson
"Verified means live, not mock" was in force the whole time; I had filed it under prod data, not under
the daemon's own runtime. Interactive and headless are different environments and I read the
interactive one as ground truth for the other.

What changed (PR #48 on vibrant-america-auto):
- `CLAUDE.md` in that repo with the table and five rules: live check before the PR with its output in
  the PR body; environment facts come from the environment (`probe`, `claude -p --debug=mcp`,
  `gh pr view --json baseRefName`), never from the interactive session's tool list; no stacked PRs;
  reinstall only when idle (`install.sh` now waits for live runs); say what was verified in those words.
- `python -m vibrant_america_auto probe`: one headless call (~$0.3) that prints the tools a profile
  really sees per server and the MCP servers that failed. Running it before #46 would have shown the
  connector prefix in 60 seconds.

Lessons for every repo, not only this one:
1. A unit test with a fake proves the Python around the fake; it cannot prove a name, a flag or a
   timing that the fake was written to match. When the risk is "I assumed how the environment behaves",
   the verification is a run in that environment, and the report names it.
2. Cost asymmetry: each of these facts was checkable for under a dollar and a minute before the PR;
   each cost Leo a report, me a follow-up PR, and once a lost approval.
3. "Done" in a report means "verified live" unless it says otherwise. Writing "148 tests pass" is
   allowed; writing it where "it works" is expected is the mistake.
