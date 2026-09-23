You are running as a scheduled one-shot job on 2026-09-30 for VP-18324.

Background. `/proxy/old-report/downloadTestOrderPDF` on trans v1 (service
`lis-trans-deployment`) had exactly one caller, LIS-setting-consumer. On
2026-09-22 23:32Z that caller was repointed to `/trans/downloadTestOrderPDF`.
A removal notice was announced on 2026-09-23 with a one-week notice. Today is
the day the notice expires.

Your job is to decide whether the removal can proceed, and to prepare it for
Leo — never to perform it.

STEP 1 — measure, and validate the measurement before believing it.

Query Datadog for traffic on the whole `/proxy/old-report/*` family since
2026-09-23T00:00:00Z. The route path is in the `custom.url` attribute, queried
as `@url` — it is NOT in the log message, so a free-text search returns zero
for the wrong reason. Caller attribution is also available: the old-report
family emits `@operation:proxyOldReportCaller` (a label split that shipped in
trans v1 `ad5ab17` and had not yet been observed firing as of 2026-09-23, so
treat its absence as uninformative, not as evidence of zero).

Before you treat any zero as a real zero, run a positive control: the same
query shape against `/trans/downloadTestOrderPDF`, which should return hundreds
per hour. If the control returns nothing, the query or the tool is broken —
stop, and go to the NOT-SAFE path below.

STEP 2 — decide.

Traffic is ZERO on every `/proxy/old-report/*` route for the whole window, and
the positive control returned data:
  -> proceed to STEP 3.

Anything else — any request on any of those routes, a failed or unavailable
Datadog query, a positive control that returns nothing, or any result you
cannot interpret with confidence:
  -> do NOT open a PR or a ticket. Write the report, notify, and stop. Say
     plainly what you saw and why you stopped. An inconclusive check is not a
     pass; the cost of waiting another week is nothing, and the cost of
     deleting a route someone still calls is a silent 404 in a customer path.

STEP 3 — prepare the removal, do not perform it.

a) Open a Jira ticket under epic VP-18260, assigned to Leo, priority P2, titled
   for the removal, recording the measured window and the numbers you saw.
   Use the Atlassian MCP (`createJiraIssue`); the vibrant MCP returns 403 on
   issue creation.

b) Open a DRAFT pull request against `LIS-transformer` `main` from a branch
   `chore/leo/VP-18324-remove-old-report-routes`, deleting the eleven
   `/proxy/old-report/*` routes: the controller
   `src/proxy/old-report.controller.ts`, its service if nothing else uses it,
   and the registration in `src/proxy/proxy.module.ts`. Leave
   `src/trans/trans-reports.controller.ts` alone — those are the twins that
   stay. Work in a git worktree off `origin/main`, never in a checkout that is
   behind: run `git fetch` then confirm with `git status -sb` before reading
   any file, and read only from that worktree.

   Run typecheck and the test suite. Compare both against a clean `origin/main`
   rather than assuming a failure is pre-existing. If anything fails that does
   not fail on the baseline, mark the PR draft and say so in the body.

   Do not merge. Do not push to main. Do not touch any ConfigMap.

STEP 4 — report.

Write `DailyJob/proxy_old_report_removal/report_<YYYY-MM-DD>.md` with what you
measured, what you decided, and links to anything you opened. Commit and push
it to this repo's main. Then notify Leo with `osascript` — one line, saying
whether the removal is ready and where to look.

Keep the Jira ticket and the PR body in English. Your report file may be in
Traditional Chinese.
