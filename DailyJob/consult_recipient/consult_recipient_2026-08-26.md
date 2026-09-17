# Consult recipient check — 2026-08-26

Window: next 48h from 2026-08-26T13:45:04.020Z
Consults scheduled: 61 (internal clinical-team blocks skipped: 11)
**Unreachable and actionable: 3**
No address anywhere (informational, nothing to populate): 0

| event | start | reason | calendars |
|---|---|---|---|
| 13093 | 2026-08-26T20:30:00.000Z | no clinicadmin participant | 48043 (owner 30209) |
| 12955 | 2026-08-27T16:30:00.000Z | no attendee has calendar_owner_email | 34886 (owner 509005) |
| 12965 | 2026-08-27T20:30:00.000Z | no clinicadmin participant | 48043 (owner 30209) |

Fix: populate `calendar_owner_email` from the owner's LIS notification contact (VP-17825).
