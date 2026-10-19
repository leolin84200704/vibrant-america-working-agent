# LIS-Sample -> trans v1 route migration: the process every family follows

> Leo's directive 2026-10-16 (LBS-1842 / VP-18889 closeout): "這套 migration 的流程請你記下來，未來的 migration 也要 follow".
> Written from what actually happened for VP-18801, VP-18802, LBS-1842 and VP-18889; the Confluence doc step and the
> two-week Slack window are Leo's additions on 2026-10-16. Applies to every remaining family (VP-18795, VP-18797..18800)
> and to any later "move routes from service A to service B" job.

## 0. Ground rule: no route leaves the old service without a replacement

LBS-1842 came from VP-18480 removing 18 routes on traffic evidence alone. A route is removed only when all five hold:
replacement live; every code caller moved; 14 days at zero on the old route's `caller_attribution`; org-wide code search
clean; announced in the LIS dev channel with the route list and date.

## 1. Port (per family, one ticket)

1. Port the controller + service + DTOs from the legacy repo **verbatim** (same paths, verbs, status codes, bodies,
   `{code, message}` error shape, declaration order). Mark any deliberate difference in the class doc comment
   (e.g. "LIS-Sample has no guard here; trans requires a token") and in the PR body.
2. Unit tests for every new handler and every branch; regenerate contracts (`npm run contracts:gen`) and commit them;
   `npm run contracts:check` must say "up to date".
3. Worktree per branch under `~/src/LIS-transformer.worktrees/<name>`; give it a **real** `node_modules`
   (`cp -a` from a sibling, or APFS clone `cp -ac`). A symlinked node_modules makes tsc fail the pre-push build with
   TS2742 "cannot be named without a reference to ../../other-worktree/node_modules" (2026-10-16).
4. Branch off `main` -> PR to `main` (Leo merges). Cherry-pick onto `origin/stage_test` -> twin PR to `stage_test`
   (agent merges). On the stage twin keep stage_test's `contracts/` (regenerating there picks up unrelated drift);
   the main PR carries the reviewed contract diff.
5. Pre-push hook runs build + DI smoke; CJK grep; no lint step in CI (the `require` in `jest.mock('async-retry')`
   is the shared pattern, leave it).

## 2. Staging: A/B against the legacy service, same token, same requests

- A = legacy service port-forward (LIS-Sample staging `-n sample svc/lis-sample-service-staging 16399:16300`),
  B = trans staging (`svc/lis-trans-service-st 3147:3147`). Token: HS256 minted from `lis-sample-secret-dev`
  `AUTH_JWT_SECRET`, claims `{user_id: 69154, role: admin, user_roles: [admin], username: lis.results}`.
- Harness: `smoke.mjs` (cases JSON -> status + sorted-body diff per case). Cover for every route: real-id read,
  404 / unknown id, non-numeric id (500 parity), no token (401), each 400 validation branch, and the writes
  (do them on staging; use ids that already exist, idempotent where possible). For create/patch/delete families run
  the full lifecycle on each side and confirm nothing is left behind.
- Confirm from the pod log that B actually handled the writes (request/response lines on the new pod).
- **Two stage deploys that finish in the same second race**: the older image can land last. After merging two
  twins back to back, check `kubectl get deploy ... -o jsonpath='{.spec.template.spec.containers[0].image}'` and
  re-run only the `deploy` job of the newer run (`gh run rerun --job <id>`) if it lost (2026-10-16).
- Restart the port-forward after every pod roll; close all port-forwards at the end.

## 3. Production

1. Leo merges the main PR(s). If a second main PR conflicts on `contracts/`, merge `origin/main` into the branch,
   regenerate contracts, run the sample jest tree, push, and leave a PR comment naming the new head SHA
   (one-PR-one-head rule); Leo may authorise the agent to merge that one.
2. Wait for `lis-transformer-deploy-prod`; verify the deployment image is the newest SHA (same race as staging) and
   3/3 pods; scan new pods for new error classes (known boot warnings: `DATABASE_URL_VA_INFO_MASTER/SLAVE`,
   Service Bus key, Redis).
3. **Prod A/B is read-only**: A = `-n sample svc/lis-sample-service 16398:16300`, B = `svc/lis-trans-service 3146:3146`,
   token minted from `lis-sample-secret-prod` (scratchpad only, never printed or committed). Real ids discovered
   through A first. Only GETs and validation / 401 / 404 paths; no row-changing calls. Check the equal cases carry
   non-empty real data before calling them equal.
4. Also probe the **public ingress** once per environment (`/v1/portal/trans-service/<path>` prod,
   `/v1/portal/trans-service-st/<path>` staging): the doc below must quote URLs that were actually called.

## 4. Closeout (all four, in this order)

1. Jira: family ticket(s) -> Dev Complete via Atlassian MCP (Leo's account); one comment per ticket with PRs,
   prod SHA, A/B result, deliberate differences, "no traffic moves until the callers switch / VP-18803".
2. Confluence: a "before / after for callers" page in Leo's folder
   `wiki/spaces/~712020f48ab0dd13b5404191734281747e6a10/folder/2119335937` (Transformer-module-rewrite):
   base-URL table per environment (public + in-cluster), the route list that can switch today, what is NOT on trans
   yet, behaviour differences, per-caller "the one line to change" (file + line), verification evidence, rollback,
   the removal rule. First page: "LIS-Sample routes now served by trans v1: what callers change (before / after)".
   For later families **update that page** (add rows, move routes from "not yet" to "switch today") rather than
   creating a sibling.
3. The agent drafts the announcement; Leo posts it in Slack **#developers** (`C02AQGMU422`) with a **two-week**
   deadline. The agent does not post to Slack. Posted so far: 2026-10-16 (29 routes, deadline 2026-10-30) and
   2026-10-19 (44 routes, deadline 2026-11-02).
4. After the window: add the routes and the deadline to `DailyJob/lis_sample_route_removal/routes.json`. That
   daily job checks `caller_attribution` (14 days at zero) and the org-wide code search per route and opens a
   draft removal PR on LIS-Sample for the eligible ones; Leo merges. The ingress rewrite / scale-down stays with
   VP-18803. STM + journal for the ticket; this runbook updated if the process changed.

## 5. Artifacts from the first run (2026-10-16)

- Confluence page created under the folder above (link in LBS-1842 STM). Jira: VP-18801, VP-18802, VP-18889 Dev Complete.
- Scratchpad harness files (`smoke.mjs`, `cases-read.json`, `cases-write.json`, `cases-prod.json`,
  `notif-lifecycle.mjs`) are session-local; re-create from the descriptions above.
