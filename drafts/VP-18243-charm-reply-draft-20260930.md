# VP-18243 — draft reply to ChARM Support (NOT SENT)

Prepared 2026-09-30, revised to remove every question ChARM has already answered
(their 2026-09-24 reply on the 37-row mapping table, and the 2026-09-28 letter).
English. To be reviewed by Leo, then sent by Mingxi Li / customer service.
Figures are from prod `lis_emr` as of 2026-09-30.

**Deliberately NOT asked again, because ChARM already answered it:**
- whether the 142 undelivered results reached them (2026-09-28: "never received, misplaced, or
  delivered to the wrong place on our end")
- whether the providers mapped to `P00029HUC092017` are members of that practice (2026-09-24: every
  provider under that code is a registered member, and their 15-clinic list matched ours exactly)
- the never-exercised mappings other than Melissa Jones (2026-09-24: reviewed against our 37-row table,
  "no other discrepancies")
- the numeric codes 126423 and 33677 (same review, not flagged)

---

Hi ChARM Support team,

Thank you for the detailed answers. They resolved the open questions on our side and let us close
several gaps immediately. This note is mostly to confirm what we have changed, so that our records and
yours agree. There are only three things we still need from you, at the end.

## 1. What we have changed on our end

**Wild Oak Medicine.** Confirmed, thank you. We had a second configuration for this practice that was
sending `16289` as the receiving facility. We corrected it to `P00058WOM030323` on 2026-09-28 and
re-sent the six results that had been affected. All six were acknowledged by your system with
`MSA|AA`, so this practice is now fully reconciled.

**The six practices with no interface.** Understood: there is no receiving-facility code for us to
correct, because no interface was ever established. We switched off all six configurations on
2026-09-30 and recorded your statement against each one. No further results will be sent to them, and
none can be re-enabled until an interface exists and you have supplied the code. For your records,
these are the results we had generated for them, none of which reached anyone:

| Practice (our name for it) | value we had been sending | results generated, never delivered |
|---|---|---|
| Holistique Naturopathic Medical Center | 19339 | 92 |
| Options Naturopathic | 26445 | 29 |
| Dr. Dana Cohen | 17969 | 17 |
| Northland Prairie Care | 127778 | 3 |
| Eudaimonia Sacred Health | 150676 | 1 |
| Nature Med Integrative Medicine | 128115 | 0 |
| **Total** | | **142** |

On the strength of your confirmation that rejected messages are never received, stored or delivered
anywhere, we are informing these practices that none of these results reached them and arranging
delivery through another channel. No action needed from you on this point.

**Dr. Geyer.** Understood, and thank you for confirming the routing logic. Her integration has been
switched off on our side since 2026-09-11 and her results have been held since then rather than being
delivered to Holistic Urgent Care & Primary Care. Whether her other two practices should have their own
interfaces is a decision for the practices, and we are taking it up with them directly; if they decide
to proceed we will follow the lab-onboarding process you described.

The same applies to the other individual provider accounts we have mapped to `P00029HUC092017`. You
confirmed on 2026-09-24 that every provider under that code is a registered member of Holistic Urgent
Care & Primary Care, so the technical mapping is not in question. What remains is whether each
provider intends their results to be delivered to that practice, and we are resolving that with the
practices rather than with you.

**Unrecognized receiving facility.** Thank you for confirming that such messages are rejected on
arrival and never stored, filed or delivered to any practice. That closes the misdelivery question.

## 2. What we still need from you

**Q1 — HL7 version.** While investigating, we found that every message your system answered with an
empty response body rather than an HL7 acknowledgement had been sent by us as **HL7 version 2.3**,
while every message we send as **2.3.1** receives a proper `MSA|AA` or `MSA|AE`. We have corrected all
our configurations to 2.3.1. Is 2.3.1 the required version for your results interface, and should we
treat any 2.3 message we sent in the past as never accepted?

**Q2 — Empty response.** Related to the above: when your system returns an empty response body instead
of an acknowledgement, should we always treat that as a non-delivery? We would like to raise an alert
on it rather than assume success, which is what our system did until now.

**Q3 — One new provider, not part of the list you reviewed on 2026-09-24.** We received an integration
request for **Melissa Jones** on 2026-09-24, after we sent you the mapping table, so it was not
included in your review. It was approved on our side on 2026-09-28 but we put it on hold before any
result was sent, because it carried an automatically generated value rather than a ChARM
receiving-facility code. Does this provider's practice have a ChARM interface with us, and if so what
is the correct receiving-facility code? If there is no interface, we will leave the request on hold and
treat it the same way as the six practices above.

One optional extra, only if it is easy for you to answer: for a practice that later completes
onboarding, is there a supported way to have historical results loaded into their account, or should
those be provided to the practice outside the interface? This affects how we hand over the 142 results
above, but it is not blocking us.

Thank you again for the clear answers.

Best regards,
Vibrant America
