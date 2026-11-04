---
date: 2026-11-03
ticket: VP-19159
type: journal
tags: [cerbo, maristany-medical, report-group, per-report, emr-v2]
related: [VP-19008, VP-19046, VP-18833]
distilled: true
---

# VP-19159: second report group (TB1 + VA) on the VP-19008 machinery

## What happened
New ticket via the watcher. Clinic wants Tickborne 1.0 and Immunoglobulins in one report again. Investigation was prod read-only: rtr scope keys showed REPORT:TB1 + REPORT:VA, OBR names identified VA as Total Immunoglobulins, and order_test_details showed Immunoglobulins is a separate free add-on test group (167), not a bundle.

## Reasoning worth keeping
- Leo read result_push_level = WHOLE_ORDER and concluded the clinic gets one file. The two settings are orthogonal: push level = when, split_result_pdf_by_report (on an HL7-only vendor) = how the push is cut into messages. Answer with both columns plus the code line, not with a description.
- A group triggered by "reports present" would hold a lone TB1 forever when VA was never ordered. The trigger has to come from what was ordered (line items), and only from ids confirmed to render the member reports (63 yes, 590 unconfirmed -> excluded). An unconfirmed id is not a harmless extra: it can create a permanent hold.
- A group whose file name differs from its key (fileKey TB1 vs key TBI) breaks the endsWith(_key.hl7) dedup. A test with a mock that honours endsWith caught that, and the test that expected TB1 to be "outside any group" had to move to another report.
- Leo replied "我看不懂，請詳細介紹" to the first proposal: it was a dense list of codes (REPORT:TB1, test group ids). The second version worked: a plain timeline (before 10-15 / after 10-15 / after VP-19008), then why TTB's rule does not fit, then the change, then the decisions with recommendations.

## Mechanics
- The emr-v2 main checkout's node_modules lacks pdf-lib (it is on another branch). Symlink node_modules from the VP-19008 worktree, then run prisma generate.
- lis_ordermanage join: orders.id = order_test_details.order_test; orders.sample_id gives the sample.
