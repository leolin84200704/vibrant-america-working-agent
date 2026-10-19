You are running as a scheduled daily job: the LIS-Sample route-removal check.

Background. LIS-Sample routes were ported to trans v1 and announced in Slack
#developers (C02AQGMU422) with a switch deadline per batch. The list of routes,
their batch, and each batch's deadline are in
`DailyJob/lis_sample_route_removal/routes.json`. Routes already handled (a
removal PR opened) are in `DailyJob/lis_sample_route_removal/state.json`
(create it as `{"handled": {}}` if missing). The removal rule (Leo, 2026-10-16,
`runbooks/lis-sample-route-migration.md` section 0) is: a route leaves
LIS-Sample only when its replacement is live, every code caller moved, 14 days
at zero on LIS-Sample `caller_attribution`, an org-wide code search is clean,
and the removal was announced. Replacement and announcement are already true
for every route in routes.json.

Your job is to decide which routes are eligible today and prepare their removal
for Leo, never to perform it.

STEP 0 - sync. `git fetch` and `git status -sb` in this repo and in
`~/src/LIS-Sample` (branch master); pull if behind. Read state.json.

STEP 1 - candidates. Every route in routes.json whose batch deadline is before
today (America/Los_Angeles) and that is not in state.handled.

STEP 2 - measure, and validate the measurement before believing it.
For each candidate, count requests in the last 14 days with Datadog logs
(analyze_datadog_logs, SQL count, grouped):
  filter: `service:lis-sample-deployment* @event:caller_attribution @method:<METHOD> @route:"<PATH>"`
  (`@route` holds the route template exactly as in routes.json, e.g.
  `/record-management/providers/:customer_id/patients`; it is NOT in the log
  message, so a free-text search returns zero for the wrong reason.)
Group the non-zero ones by `@user_agent` and `@claims.internal_user_name` so
Leo can see who still calls them.
Positive control first, with the same query shape: `@method:GET @route:"/order"`
must return thousands over 14 days. If the control returns nothing, the query or
the tool is broken: stop and go to the REPORT-ONLY path.

STEP 3 - code search. For each candidate with zero traffic, search the org for
the route's static path prefix (drop `:param` segments and anything after them):
`gh search code --owner Vibrant-America "<static path>" --limit 50`, ignoring
hits in LIS-Sample, LIS-transformer and LIS-transformer-v2. Any other hit that is
a real call (not a comment, doc, or test fixture) makes the route NOT eligible;
record the repo, file and line. If `gh search code` fails, treat every candidate
as not eligible today.

STEP 4 - decide. Eligible = zero in 14 days AND positive control OK AND code
search clean. Everything else waits; waiting costs nothing, deleting a route
someone still calls is a silent 404 (LBS-1842).

STEP 5 - prepare the removal (only if at least one route is eligible).
Open ONE draft pull request against `Vibrant-America/LIS-Sample` `master` from
branch `chore/leo/remove-migrated-routes-<YYYYMMDD>`, working in a git worktree
off `origin/master` under `~/src/LIS-Sample.worktrees/`. Remove only the
eligible handlers. When a path keeps another verb (for example `GET /order/check`
stays while `POST /order/check` goes), remove only that verb's handler. Remove a
service method, DTO or module only when nothing else references it. Keep the
removal mechanical and minimal; do not refactor.
Run the build and the unit tests on the branch and on a clean `origin/master`;
say in the PR body whether anything fails that does not fail on the baseline.
PR body (English): the routes removed, the 14-day window measured, the counts
(all zero), the positive-control count, the code-search result, the Slack
announcement and deadline, and "Do not merge before Leo reviews". Do not merge,
do not push to master, do not touch any ConfigMap, ingress, or deployment.
Add each removed route to state.json `handled` with the PR URL and today's date.

STEP 6 - report. Write `DailyJob/lis_sample_route_removal/report_<YYYY-MM-DD>.md`
(Traditional Chinese is fine): positive control, per-route counts, who still
calls the non-zero routes, code-search hits, what was opened. Commit
`routes.json`-unchanged, `state.json` and the report to this repo's main and
push. Notify Leo with one `osascript` line: how many routes are ready (PR link)
and how many still have callers.

REPORT-ONLY path: write the report saying exactly what failed or was
inconclusive, commit it, notify, open nothing.

Never post to Slack or Jira. Never merge. Never delete anything outside the
draft PR.
