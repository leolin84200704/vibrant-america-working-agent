---
id: 2026-11-13-vp19339-healthie-client-id
type: journal
date: 2026-11-13
tickets: [VP-19339, VP-19337, VP-19338, VP-19341]
tags: [healthie, jag, patient-mapping, emr-v2, lis_emr, prisma, grpc]
distilled: false
---
# VP-19339: practice-scoped Healthie client id, draft PR #545

Trigger: new ticket from Xiaoye under epic VP-19337. My first proposal listed a column on
lis_core_v7.patient as one option. Leo answered that core_7 tables are off limits and asked why any of
this is needed. Explaining the reason (Healthie API needs its own client id; JAG patients cannot be
matched by name or DOB) and two options with pros and cons got a clear choice: a lis_emr table owned by
emr-v2.

Lesson: when proposing storage, do not list a core table change as an option at all unless the ticket
requires it. Leo reads the option list as the plan.

Build notes:
- emr-v2 cannot read lis_core_v7 directly. Patient-in-practice is getPatientById owners intersected with
  listClinicCustomerIds, both gRPC.
- Prisma @@unique needs `name:` for the compound key name used in findUnique; `map:` only names the DB index.
- Fresh worktree: `npm ci` (about 40 s) plus `prisma generate` for both schema.prisma and
  schema.test.prisma, otherwise 5 integration-management suites fail on the missing test client.
- The in-memory Prisma double that enforces the unique keys caught a real ordering issue: read the
  previous id before the update, not from the row object afterwards.
- I kept "replace never steals an id from another patient" even though the plan text read as if replace
  overrides both conflicts. Flagged in the PR and STM.

Open: DDL on staging and prod, staging test, JAG file format, VP-19338 wiring of the pending-report send.
