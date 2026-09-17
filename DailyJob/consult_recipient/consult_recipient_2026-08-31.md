# Consult recipient check — 2026-08-31

Window: next 48h from 2026-08-31T13:45:06.096Z
Consults scheduled: 44 (internal clinical-team blocks skipped: 9)
**Unreachable and actionable: 2**
No address anywhere (informational, nothing to populate): 0

| event | start | reason | calendars |
|---|---|---|---|
| 13127 | 2026-08-31T16:00:00.000Z | no clinicadmin participant | 48043 (owner 30209) |
| 12616 | 2026-09-01T18:30:00.000Z | no attendee has calendar_owner_email | 39293 (owner 501223) |

Fix: populate `calendar_owner_email` from the owner's LIS notification contact (VP-17825).
