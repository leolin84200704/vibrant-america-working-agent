# VP-18243 — draft reply to ChARM Support (NOT SENT)

Prepared 2026-09-30. English. To be reviewed by Leo, then sent by Mingxi Li / customer service.
Every figure below is from prod `lis_emr` as of 2026-09-30.

---

Hi ChARM Support team,

Thank you for the detailed answers, they resolved the open questions on our side and let us close
several gaps immediately. Below is what we have already changed, one finding from our own
investigation that affects you, and the remaining items we still need confirmed.

## 1. What we changed on our end

**Wild Oak Medicine.** Confirmed, thank you. We had a second configuration for this practice that was
sending `16289` as the receiving facility. We corrected it to `P00058WOM030323` on 2026-09-28 and
re-sent the six results that had been affected. All six were acknowledged by your system with
`MSA|AA`, so that practice is now fully reconciled.

**The six practices with no interface.** Understood: there is no receiving-facility code for us to
correct because no interface was ever established. We have switched off all six configurations on our
side on 2026-09-30 and recorded your statement against each one, so no further results will be sent to
them and none can be re-enabled until an interface exists and you have supplied the code:

| Practice (our name for it) | value we had been sending | results generated but never delivered |
|---|---|---|
| Holistique Naturopathic Medical Center | 19339 | 92 |
| Options Naturopathic | 26445 | 29 |
| Dr. Dana Cohen | 17969 | 17 |
| Northland Prairie Care | 127778 | 3 |
| Eudaimonia Sacred Health | 150676 | 1 |
| Nature Med Integrative Medicine | 128115 | 0 |
| **Total** | | **142** |

**Dr. Geyer.** Understood, and thank you for confirming the routing logic. Her integration has been
switched off on our side since 2026-09-11 and her results have been held since then rather than being
delivered to Holistic Urgent Care & Primary Care. We are taking the question of whether her other two
practices should have their own interfaces back to the practice, and will follow the lab-onboarding
process you described if they decide to proceed.

**Unrecognized receiving facility.** Thank you for confirming that such messages are rejected on
arrival and never stored, filed or delivered to any practice. That closes the misdelivery question for
the six practices above.

## 2. One finding on our side that you may want to be aware of

While investigating, we found that the messages your system was answering with an empty response body
(rather than an HL7 acknowledgement) were all being sent by us as **HL7 version 2.3**, while every
message we send as **2.3.1** receives a proper `MSA|AA` or `MSA|AE`. We have corrected all our
configurations to 2.3.1.

Two things we would like to confirm:

- **Q1.** Is 2.3.1 the required version for your results interface, and should we treat a 2.3 message
  as never accepted?
- **Q2.** When your system returns an empty response body rather than an acknowledgement, should we
  always treat that as a non-delivery? We would like to alert on it rather than assume success.

## 3. The 142 results that were never delivered

- **Q3.** Can you confirm that none of the 142 results listed in the table above were received on your
  side in any form, so that we can state that clearly to the practices?
- **Q4.** For practices that later complete onboarding, is there a supported way to have historical
  results loaded into their account, or should those results be provided to them outside the
  interface? We can produce a full list of the affected accessions and patients on request.

## 4. Mappings we need you to confirm

These configurations exist on our side but no result has ever been sent through them, so your system
has never had the opportunity to accept or reject them. We would like to confirm them **before** the
first result is sent, rather than discover a problem afterwards.

**Q5. Twelve individual provider accounts we have mapped to `P00029HUC092017`
(Holistic Urgent Care & Primary Care).** Each of these is that provider's own account in our system,
and each is currently configured so that its results would be delivered to Holistic Urgent Care &
Primary Care. This is the same pattern that produced the Dr. Geyer case, so we would like each one
confirmed individually before any result is sent:

| Provider / account name on our side |
|---|
| Erin Ellis |
| Robyn Wright |
| Corrine Poulin |
| Rebecca Irwin |
| McKenzie Siemion |
| Nicolas Figueredo |
| Swikar Patel |
| Ebrahim Jatta |
| Holistic Urgent Care & Primary Care (4 further separate accounts we hold under this name) |

For each: is this provider a registered member of the Holistic Urgent Care & Primary Care practice in
ChARM, and should their results be delivered to `P00029HUC092017`?

**Q6. Six further mappings that have never been exercised.** Please confirm the practice each code
belongs to and that the account we have mapped to it is correct:

| Receiving facility | Account name on our side |
|---|---|
| P00037VHL082218 | The Center for Fully Functional Health (Dr. Ellen Antoine / Dr. Scott) |
| P00021NMC1128 | Nourish (a second account, in addition to the one already delivering successfully) |
| P00036PIM051618 | Pure Health Medicine (a second account, as above) |
| P00058WOM030323 | Thea Rabb |
| P00055AIM051222 | Ageless Integrated Medicine |

**Q7. Melissa Jones.** We have a new integration request for this provider that was approved on our
side on 2026-09-28. We have put it on hold before any result was sent, because it carried an
automatically generated value rather than a ChARM receiving-facility code. Does this provider's
practice have a ChARM interface with us, and if so what is the correct receiving-facility code? If not,
we will leave the request on hold.

**Q8. Two numeric receiving-facility values that your system accepts.** Your system returns `MSA|AA`
for these two and echoes them back, so they appear to be valid, but they do not follow the `P00...`
pattern of every other code. Please confirm they are intentional so that we do not "correct" them by
mistake:

| Value | Account name on our side |
|---|---|
| 126423 | Functional Medicine Collaborative |
| 33677 | Aura Functional Medicine |

Thank you again for the clear answers. The practices whose results your system is already
acknowledging - Nourish, The Healing Collective, Holistic Urgent Care & Primary Care, Natural Family
Health Clinic, Bear Creek Naturopathic, Wild Oak Medicine, Creosote Health Services, Pure Health
Medicine, Pure Health Encinitas, Functional Medicine Collaborative and Aura Functional Medicine - need
no action from you; we have verified those mappings from your acknowledgements and they are not part
of the questions above.

Best regards,
Vibrant America
