# Consult recipient check — 2026-09-09

Window: next 48h from 2026-09-09T13:45:05.570Z
Consults scheduled: 61 (internal clinical-team blocks skipped: 9)
**Unreachable and actionable: 2**
No address anywhere (informational, nothing to populate): 0

| event | start | reason | calendars |
|---|---|---|---|
| 13084 | 2026-09-09T20:30:00.000Z | no attendee has calendar_owner_email | 34886 (owner 509005) |
| 13235 | 2026-09-10T16:30:00.000Z | no attendee has calendar_owner_email | 34886 (owner 509005) |

Fix: populate `calendar_owner_email` from the owner's LIS notification contact (VP-17825).
