# VP-18324 — one-shot removal check, 2026-09-30

`/proxy/old-report/downloadTestOrderPDF` on trans v1 had exactly one caller,
LIS-setting-consumer. On 2026-09-22 23:32Z that caller was repointed to
`/trans/downloadTestOrderPDF`; a removal notice was announced on 2026-09-23 with
one week's notice. This job runs the day the notice expires.

## What it does

1. Measures traffic on the whole `/proxy/old-report/*` family since the cutover.
2. **Only if it is genuinely zero**, opens a Jira ticket under VP-18260 and a
   **draft** PR against `LIS-transformer` that deletes the eleven routes.
3. Writes `report_<date>.md` here, commits it, and notifies Leo.

It never deletes a route, never merges, and never touches a ConfigMap. Every
outcome ends with a human holding the decision.

## What makes it stop instead of proceed

Any of these and it writes the report, notifies, and opens nothing:

- any request on any `/proxy/old-report/*` route in the window
- a Datadog query that fails or is unavailable
- **a positive control that returns nothing** — the prompt requires checking
  `/trans/downloadTestOrderPDF` (hundreds per hour) with the same query shape
  first, because a zero from a broken query looks exactly like a real zero
- any result it cannot interpret with confidence

Waiting another week costs nothing. Deleting a route someone still calls is a
silent 404 in a customer-facing path.

Two traps the prompt names explicitly, because both have already caught us on
this ticket:

- the route path lives in the `custom.url` attribute, **not** in the log
  message, so a free-text search for `old-report` returns zero for the wrong
  reason
- `@operation:proxyOldReportCaller` shipped in trans v1 `ad5ab17` but had not
  been observed firing as of 2026-09-23 (the route had already gone quiet), so
  its absence is uninformative rather than evidence of zero

## One-shot semantics

launchd's `StartCalendarInterval` with `Month`+`Day` fires again on the same
date next year, so the runner disarms itself twice over:

- `.done` marker, checked on entry — the one that actually guarantees it
- `launchctl bootout` after a completed run — best-effort

A run that **fails** deliberately does not write the marker. A job that never
ran must fire again rather than quietly disarm itself.

## Install / remove

```bash
cp DailyJob/proxy_old_report_removal/com.lis.proxy-old-report-removal.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.lis.proxy-old-report-removal.plist

# cancel it
launchctl bootout gui/$(id -u)/com.lis.proxy-old-report-removal
rm ~/Library/LaunchAgents/com.lis.proxy-old-report-removal.plist
```

Model is pinned (`REMOVAL_MODEL`, default `fable`) — an unpinned `claude -p`
could change between the day this was written and the day it fires, which for a
job that opens a PR is not a difference worth discovering in production.

Logs: `launchd_stdout.log` / `launchd_stderr.log` here.
