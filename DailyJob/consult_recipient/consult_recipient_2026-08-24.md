# Consult recipient check — 2026-08-24

Window: next 48h from 2026-08-24T22:21:11.057Z
Consults scheduled: 63 (internal clinical-team blocks skipped: 12)
**Unreachable and actionable: 1**
No address anywhere (informational, nothing to populate): 0

| event | start | reason | calendars |
|---|---|---|---|
| 12939 | 2026-08-25T16:00:00.000Z | no attendee has calendar_owner_email | 55522 (owner 503568) |

Fix: populate `calendar_owner_email` from the owner's LIS notification contact (VP-17825).
