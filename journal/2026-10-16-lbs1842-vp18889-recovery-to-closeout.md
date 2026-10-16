---
date: 2026-10-16
tickets: [LBS-1842, VP-18889, VP-18801, VP-18802]
type: session
summary: Session killed mid-port; recovered two uncommitted trans ports, took them through staging A/B, main merge, prod A/B, Dev Complete x3, a Confluence caller guide and a recorded migration process.
---

# LBS-1842 / VP-18889: recovery to closeout

## What happened
- Previous session was force-closed while two subagents were porting routes into trans worktrees. Nothing was committed, but the working trees were complete (code, specs, regenerated contracts). Recovery = verify, not redo: diffed each service body against LIS-Sample master, ran the suites, then committed.
- Pre-push build failed on 21x TS2742 because the worktrees' node_modules were symlinks into other worktrees. Real copies fixed it; APFS clones (`cp -ac`) made the stage twins instant.
- Two stage_test deploys finished in the same second and the older image won. Caught by checking the deployment image, fixed by re-running only the deploy job. Same check applied on prod (no race there).
- Staging A/B (reads, validation, writes, notification lifecycle) and prod read-only A/B both identical apart from the intended token requirement on GET /customers.
- Leo: main stays Leo's to merge (asked explicitly, answered "等 Leo merge"); then both approved, #961 conflicted on generated contracts after #960, Leo authorised the agent to resolve and merge it.
- Closeout per Leo: three tickets Dev Complete, Jira comments, Confluence before/after page in his folder, Slack post is his with a two-week window, and the process is now `runbooks/lis-sample-route-migration.md` + a CLAUDE.md rule.

## Reasoning worth keeping
- "Tests pass" written by the same agent that wrote the code is not verification; the line-by-line diff against the legacy source was the check that mattered for a verbatim port.
- The public ingress probe at the end turned a doc assumption (`/v1/lis/trans-service/samples/*`, from Phase A) into the real URL (`/v1/portal/trans-service/<path>`); the caller guide quotes only URLs that were actually called.
- The wellness portal's only LIS-Sample call points at an on-prem dev instance; surfaced as a fact for the owner, not fixed.
