You are running as a scheduled daily job: the LIS-Sample route-removal check.

Background. LIS-Sample routes were ported to trans v1 and announced in Slack
#developers (C02AQGMU422) with a switch deadline per batch. The list of routes,
their batch, and each batch's deadline are in
`DailyJob/lis_sample_route_removal/routes.json`. Routes already handled (a
removal PR opened) are in `DailyJob/lis_sample_route_removal/state.json`
(create it as `{"handled": {}}` if missing). The removal rule (Leo, 2026-11-02, replacing the
2026-10-16 traffic gate) is: a route leaves LIS-Sample at its batch's announced
deadline. Remaining traffic and code callers do NOT block the removal; they are
measured so the PR tells Leo who will get a 404. Replacement and announcement
are already true for every route in routes.json.

Your job is to prepare the removal of every route past its deadline for Leo,
never to perform it.

STEP 0 - sync. `git fetch` and `git status -sb` in this repo and in
`~/src/LIS-Sample` (branch master); pull if behind. Read state.json.

STEP 1 - candidates. Every route in routes.json whose batch deadline is before
today (America/Los_Angeles) and that is not in state.handled.

STEP 2 - measure who still calls them (informational, never a gate).
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
the tool is broken: say so in the PR body and the report ("callers unknown"),
and continue.

STEP 3 - code search (informational, never a gate). For each candidate, search
the org for the route's static path prefix (drop `:param` segments and anything
after them): `gh search code --owner Vibrant-America "<static path>" --limit 50`,
ignoring hits in LIS-Sample, LIS-transformer and LIS-transformer-v2. Record each
real call (not a comment, doc, or test fixture) as repo, file and line. If
`gh search code` fails, say so and continue.

STEP 4 - decide. Eligible = every candidate from STEP 1. Leo decided on
2026-11-02 that the announced deadline is the cut-off; the callers found in
STEPS 2-3 go into the PR body as "will get 404 after deploy", they do not hold
a route back.

STEP 5 - prepare the removal (only if at least one route is eligible).
First check for an open PR on LIS-Sample from a `chore/leo/remove-migrated-routes-*`
branch that already removes a candidate; mark such routes handled with that PR
URL instead of removing them twice.
Open ONE draft pull request against `Vibrant-America/LIS-Sample` `master` from
branch `chore/leo/remove-migrated-routes-<YYYYMMDD>`, working in a git worktree
off `origin/master` under `~/src/LIS-Sample.worktrees/`. Remove only the
eligible handlers. When a path keeps another verb (for example `GET /order/check`
stays while `POST /order/check` goes), remove only that verb's handler. Remove a
service method, DTO or module only when nothing else references it. Keep the
removal mechanical and minimal; do not refactor.
Run the build and the unit tests on the branch and on a clean `origin/master`;
say in the PR body whether anything fails that does not fail on the baseline.
PR body (English): the routes removed, the Slack announcement and deadline,
"Removed at the announced deadline by owner decision (2026-11-02)", the
14-day counts with the positive-control count, every remaining caller (user
agent / user, and code-search hits) under "Will get 404 after deploy", a route
inventory (handler count on master vs the branch, diff = exactly the removed
routes), and "Do not merge before Leo reviews". Do not merge,
do not push to master, do not touch any ConfigMap, ingress, or deployment.
Add each removed route to state.json `handled` with the PR URL and today's date.

STEP 6 - report. Write `DailyJob/lis_sample_route_removal/report_<YYYY-MM-DD>.md`
(Traditional Chinese is fine): positive control, per-route counts, who still
calls the non-zero routes, code-search hits, what was opened. Commit
`routes.json`-unchanged, `state.json` and the report to this repo's main and
push. Notify Leo with one `osascript` line: how many routes are ready (PR link)
and how many of them still have callers.

REPORT-ONLY path (the LIS-Sample build or worktree cannot be prepared): write
the report saying exactly what failed, commit it, notify, open nothing.

Never post to Slack or Jira. Never merge. Never delete anything outside the
draft PR.
