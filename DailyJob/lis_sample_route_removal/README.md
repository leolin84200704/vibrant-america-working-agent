# LIS-Sample route removal - daily check

The 73 LIS-Sample routes ported to trans v1 were announced in Slack #developers
(C02AQGMU422): batch 1 (29 routes) on 2026-10-16, deadline 2026-10-30; batch 2
(44 routes: record-management, patients, order) on 2026-10-19, deadline
2026-11-02. `routes.json` lists every route with its batch.

Leo asked (2026-10-19) for the old endpoints to be cleared automatically once
the deadline passes. This job does that within the removal rule of
`runbooks/lis-sample-route-migration.md` (section 0, adopted after LBS-1842):

- runs daily at 09:00 from 2026-10-31;
- for every route past its deadline: 14 days of LIS-Sample `caller_attribution`
  (with a positive control) and an org-wide code search;
- routes at zero with no code caller go into one **draft** PR on LIS-Sample;
  routes still called are reported with who calls them;
- `state.json` records what has a PR; the job disarms itself when every route
  is handled.

It never merges, never posts to Slack or Jira, and never touches ingress,
ConfigMaps or deployments. Leo merges the LIS-Sample PRs. The ingress rewrite
and LIS-Sample scale-down stay with VP-18803.

## Install / remove

```bash
cp DailyJob/lis_sample_route_removal/com.lis.lis-sample-route-removal.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.lis.lis-sample-route-removal.plist

launchctl bootout gui/$(id -u)/com.lis.lis-sample-route-removal
rm ~/Library/LaunchAgents/com.lis.lis-sample-route-removal.plist
```

Model pinned with `REMOVAL_MODEL` (default `opus`). Logs: `launchd_stdout.log`
and `launchd_stderr.log` here; daily findings in `report_<date>.md`.
