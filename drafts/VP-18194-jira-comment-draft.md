# DRAFT — Jira comment for VP-18194 (NOT posted; awaiting Leo's go)

---

Per-report PDF delivery is merged and deployed to production (main `280047b`), and is currently
enabled for one practice only.

**What it does**

For an integration with the split enabled, every report of the accession that is Final is rendered
on its own and delivered to that integration's existing result folder as
`{accession}_{REPORT_SHORT_NAME}.pdf`, alongside the usual `{accession}.hl7`. The HL7 message
itself is unchanged.

Two independent settings, partner-level with a per-practice override (the practice value wins; an
explicit "off" on the practice beats an "on" on the partner):

- **Split PDF by report** — default off everywhere.
- **Also deliver combined order PDF** — default on everywhere, so the combined PDF keeps arriving
  unless a partner asks us to stop it.

Both partner defaults are left off/on respectively, and enablement is done per practice. The MDHQ
(Cerbo) partner record covers 202 practices, so it is deliberately not switched on at that level.

**Delivery timing**

The PDFs go out with the practice's existing result push. Maristany Medical is configured for
whole-order delivery, so the set of PDFs arrives when the order completes. If a practice wants each
report to arrive as soon as that report is final, their existing result push level can be switched
to per-report and the PDFs follow automatically — no further development needed.

**Source of the files**

The report list and each report's PDF come from the existing report services
(`getReportStatusListV2` and the report PDF engine). A report whose PDF cannot be rendered is
recorded as a failure and simply not delivered — we never send a different report's file under its
name, and we never send a placeholder.

**Amended results — scope decision**

The acceptance criterion "an amended report triggers redelivery of all report PDFs for that order"
is **not** implemented, and we do not plan to implement it as part of this ticket. The delivery is
forward-looking only: orders that complete from now on get per-report PDFs, and orders already
delivered are not revisited.

For transparency on what this does and does not cover, we checked how amendments actually behave in
production. They arrive in batches tied to a lab ticket, and they take two forms:

1. An amendment that also re-approves results re-emits the order-completion event, so that order is
   pushed again and its per-report PDFs are regenerated and redelivered automatically.
2. An amendment that only corrects report content emits no event this service receives, so it will
   not trigger a redelivery on its own.

**If a past order, or a case in category 2, needs to reach the practice, it can be re-sent manually
through the existing result repush.** That produces the current set of per-report PDFs for that
accession. Please raise those case by case.

**Current status and what we need**

The feature is live but dormant for everyone except Maristany Medical (Practice 127660), which is
enabled as a canary.

One open item only the partner can answer: we need Cerbo to confirm that the individual PDFs
dropped in the practice's results folder are ingested and filed against the correct test. If Cerbo
consumes only the `.hl7` file and ignores additional PDFs in that folder, the delivery mechanism has
to change and we will raise that separately. Could someone on the integration side confirm with them
once the first order flows through?

Prospera / Next-Health can be enabled the same way whenever Product wants; nothing further is needed
on our side.
