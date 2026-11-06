# VP-19013 prod watch

Watches prod for the first real male EMR order of Foundation Zoomer 2.0 (868)
or Foundation Baseline (869) after the 2026-11-09 release and checks that
lis-backend-emr-v2 placed the male PSA twin (876 / 877) instead.

Leo asked for this on 2026-11-06. The swap can only be verified on a real prod
order: pricing creates 876/877 at the release, and prod HL7 traffic for
868/869 is rare (2 files in the 60 days before 2026-11-04).

- Runs at 08:13, 13:13 and 18:13 local from 2026-11-09; before that it exits.
- Each run is one headless `claude -p --model opus` with `prompt.md`.
- Read-only: Datadog logs, prod HL7 records, order readback. It never touches
  orders, DBs, Jira or Slack. Jira / QA comments are drafted in the report only.
- Writes `report_<date>.md`, updates `state.json`, commits both to main.
- Notifies (macOS) on PASS, FAIL, first sight of 876/877 live, inconclusive
  runs and the final run; silent otherwise.
- Disarms itself on the first PASS (`state.status = done`) or after 2026-12-09.

## Install / remove

```bash
cp DailyJob/vp19013_prod_watch/com.lis.vp19013-prod-watch.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.lis.vp19013-prod-watch.plist

launchctl bootout gui/$(id -u)/com.lis.vp19013-prod-watch
rm ~/Library/LaunchAgents/com.lis.vp19013-prod-watch.plist
```
