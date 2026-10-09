---
date: 2026-10-08
slug: vp18474-core-v1-http-last-call-site
related: [VP-18474, VP-18152, VP-18156, VP-18140, VP-18460, VP-18461]
distilled: true
distilled_on: 2026-10-09
---

# VP-18474: trans off core v1 HTTP — the ticket was three-quarters done before I opened it

Leo: 「ok 直接做18474」 (after I listed the shrink-line tickets), later 「901 merged. 如果從9/30到現在都沒流量就可以直接移除(請測試+執行)」.

## What I explored
- Ticket listed four core v1 HTTP call sites. Before touching code I read the linked VP-18152 (Done 09-29): Zhibin's closing comment said trans v1/v2 no longer call core over v1 HTTP for list-customer-by-id and the two create-patient routes (LIS-transformer #845, transformer-v2 #662, prod 09-30), and named the now-dead ConfigMap keys. Code grep on both repos at origin/main confirmed: the only remaining reference was `env.LOG_IN_VIA_SESSION` in trans v1 `UtilityService.login()` behind `GET /utility/login`.
- Datadog ground truth via the VP-18140 core access log (filter from `docs/plans/trans-optimization/phase3-core-v1-http-traffic.md`): trans-shaped calls last seen 09-30 00:31Z, zero after; `login_via_session` had zero callers of any kind in 15 d; trans inbound `/utility/login` zero. Remaining callers of those routes are lis-order (Java), which is Zhibin's problem for VP-18156.

## What I decided and why
- Delete the route + service method + env read, with a spec that scans PATH_METADATA so the handler cannot silently return; README endpoint table row removed and anchors re-based (no generator exists).
- Remove the four VP-18152 keys immediately (code unread since 09-30, Deployments use envFrom only), `LOG_IN_VIA_SESSION` only after each environment ran the new image. One of the removed keys was a never-expiring admin JWT in a ConfigMap — rollback copy kept outside any repo.
- No Co-Authored-By trailer on the commit (org ruleset turns it into a second-approval requirement; Leo 10-06).
- Two-week zero window was the ticket's Done-when; Leo accepted the 8-day zero plus removal and told me to execute, so the 10-14 cron was cancelled.

## What went wrong
- Symlinked node_modules for the stage_test twin: the hook failed on two deps only stage_test has. `npm ci` fixed it; postinstall rewrote tracked prisma2 generated files, discarded before commit.
- Shared generated Prisma client was stale -> false `tsc` error; `prisma generate` first.
- Two self-inflicted shell slips (line-count assert, zsh word splitting) — both caught before any effect.

## Ground truth at close
Prod + staging trans v1: `GET /utility/login` 404; ConfigMaps have zero `lis-core-http-service` values; trans pods env clean after restart; 0 errors. PRs #901 (main, merged by Leo) / #902 (stage_test, merged by me per the staging rule).
