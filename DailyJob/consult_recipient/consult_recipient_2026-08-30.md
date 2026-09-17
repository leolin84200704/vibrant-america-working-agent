# Consult recipient check — 2026-08-30

Window: next 48h from 2026-08-30T13:45:05.657Z
Consults scheduled: 10 (internal clinical-team blocks skipped: 9)
**Unreachable and actionable: 1**
No address anywhere (informational, nothing to populate): 0

| event | start | reason | calendars |
|---|---|---|---|
| 13127 | 2026-08-31T16:00:00.000Z | no clinicadmin participant | 48043 (owner 30209) |

Fix: populate `calendar_owner_email` from the owner's LIS notification contact (VP-17825).
