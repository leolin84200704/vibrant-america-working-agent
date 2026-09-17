# Consult recipient check — 2026-09-17

Window: next 48h from 2026-09-17T13:45:05.454Z
Consults scheduled: 57 (internal clinical-team blocks skipped: 8)
**Unreachable and actionable: 2**
No address anywhere (informational, nothing to populate): 0

| event | start | reason | calendars |
|---|---|---|---|
| 13523 | 2026-09-18T16:30:00.000Z | no attendee has calendar_owner_email | 43152 (owner 508114) |
| 13139 | 2026-09-18T19:00:00.000Z | no attendee has calendar_owner_email | 35893 (owner 507357) |

Fix: populate `calendar_owner_email` from the owner's LIS notification contact (VP-17825).
