# Consult recipient check — 2026-09-16

Window: next 48h from 2026-09-16T13:45:04.796Z
Consults scheduled: 60 (internal clinical-team blocks skipped: 6)
**Unreachable and actionable: 1**
No address anywhere (informational, nothing to populate): 0

| event | start | reason | calendars |
|---|---|---|---|
| 12915 | 2026-09-16T18:30:00.000Z | no attendee has calendar_owner_email | 35893 (owner 507357) |

Fix: populate `calendar_owner_email` from the owner's LIS notification contact (VP-17825).
