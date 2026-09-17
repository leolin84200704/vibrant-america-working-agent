# Consult recipient check — 2026-09-01

Window: next 48h from 2026-09-01T13:45:05.517Z
Consults scheduled: 72 (internal clinical-team blocks skipped: 8)
**Unreachable and actionable: 1**
No address anywhere (informational, nothing to populate): 0

| event | start | reason | calendars |
|---|---|---|---|
| 12616 | 2026-09-01T18:30:00.000Z | no attendee has calendar_owner_email | 39293 (owner 501223) |

Fix: populate `calendar_owner_email` from the owner's LIS notification contact (VP-17825).
