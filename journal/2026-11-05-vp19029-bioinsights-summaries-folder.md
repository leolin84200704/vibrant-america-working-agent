---
id: 2026-11-05-vp19029-bioinsights-summaries-folder
type: journal
date: 2026-11-05
tickets: [VP-19029]
tags: [bioinsights, sftp, order-summary-pdf]
distilled: true
---
# VP-19029: verify before enabling PDF delivery

Leo approved option A: check the BioInsights SFTP for the "Summaries" folder Olena named, then set
ehr_vendors 46 sftp_order_forms_path. The check came first and stopped the plan: the account sees only
/incoming and /outgoing; no Summaries folder at root, under either, or lowercase.

Decision: the plan's own fallback. No mkdir on the vendor's server, no DB write, a one-line Outlook
draft asking Olena to create /Summaries/ (or give the full path). Setting the column anyway would have
made every future order's PDF upload fail against a missing path.

Lesson: a one-word answer from a vendor ("Summaries.") names an intent, not a path. Verify existence and
write access on their side before the config change, which is why the SFTP step was ordered first.

Friction: the PEM is at ~/.ssh/bioinsights_vibrant-wellness.pem (STM pointed at ~/Downloads); macOS has
no `timeout`, use `perl -e 'alarm N; exec @ARGV'`. vibrant MCP was ECONNREFUSED, so prod was not re-read.
