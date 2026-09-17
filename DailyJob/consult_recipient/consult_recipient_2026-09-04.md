# Consult recipient check — 2026-09-04

Window: next 48h from 2026-09-04T13:45:06.044Z
Consults scheduled: 32 (internal clinical-team blocks skipped: 5)
**Unreachable and actionable: 3**
No address anywhere (informational, nothing to populate): 0

| event | start | reason | calendars |
|---|---|---|---|
| 13105 | 2026-09-04T16:00:00.000Z | no attendee has calendar_owner_email | 34830 (owner 506474) |
| 12968 | 2026-09-04T17:00:00.000Z | no attendee has calendar_owner_email | 36115 (owner 516026) |
| 13109 | 2026-09-04T20:00:00.000Z | no attendee has calendar_owner_email | 41231 (owner 502474) |

Fix: populate `calendar_owner_email` from the owner's LIS notification contact (VP-17825).
