---
id: 2026-11-11-vp19310-ttb-combined-pdf
type: journal
date: 2026-11-11
tickets: [VP-19310, LBS-1884, VP-19008]
tags: [emr-v2, cerbo, maristany, ttb, report-group, pdf]
distilled: false
---
# VP-19310: Total Tox message now carries the portal's combined PDF for TTB-only orders

Maristany's Cerbo copy of Total Tox lacked the overview pages and restarted page numbers per section. I first
thought this was the Classic/Modern switch from LBS-1884. It was not: VP-19008 builds the TTB PDF by merging
the three single-report PDFs, and that residual had already been logged for the classic case and left open.

The first version of the condition looked only at finished reports. Re-reading the VP-19008 test fixtures turned
up the Organic Acids + TTB bundle. While OAT is still pending, only the three TTB reports are final, so that
condition would embed an AllReport that lacks OAT now and then send OAT again later. So the condition now reads
the order line items: every ordered test group must be a TTB component. A failed pdf-cache download falls back
to the merge, so the change cannot hold a result back.

Mingxi had already opened VP-19310 before I would have created a ticket; check JQL for a fresh ticket
before drafting a new one.

Lesson: a known residual written only into STM ("classic TTB merge lacks the summary") comes back as a
customer complaint. When a residual is visible to the customer, it needs its own ticket at close.
