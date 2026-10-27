# LIS-Sample route removal - daily check

All 83 LIS-Sample routes are ported to trans v1 and were announced in Slack
#developers (C02AQGMU422):

| Batch | Routes | Announced | Deadline |
|---|---|---|---|
| 1 | 28 (interaction logs, tests, tubes, coupon, phlebotomists, storage, notifications, customers) | 2026-10-16 | 2026-10-30 |
| 2 | 44 (record-management, patients, order) | 2026-10-19 | 2026-11-02 |
| 3 | `GET /patients/v2/kits` (re-announced with its own deadline) | 2026-10-22 | 2026-11-05 |
| 4 | `GET /status` (VP-18795) | 2026-10-27 | 2026-11-09 |
| 5 | 9 sample-page GET routes (VP-18797) | 2026-10-27 | 2026-11-10 |

`routes.json` lists every route with its batch.

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
