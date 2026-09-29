# Reply to Olena (devcom) — V00000417.hl7 passed, 2026-09-29

Status: DRAFT, not sent. Leo reviews.

## Ground truth behind every claim below (verified 2026-09-29, prod DB + live SFTP)

| Claim in the email | Evidence |
|---|---|
| File received 2026-09-25 18:30 UTC | `lis_emr.hl7_file_input` 7196, `V00000417.hl7`, received_time 2026-09-25T18:30:05Z |
| Parsed with no errors | same row: `parse_finished=1`, `retry_num=5`, `last_error=NULL`, `emr_code_not_found=NULL`, `customer_not_found=NULL` |
| Order created | `lis_re.order_table` id 30139923543497260 — sample 2642225, accession 2609256344, patient 3286031, clinic 132493, total 570.00, source EMR |
| Both tests accepted | `lis_emr.emr_sample` 6618, `test_input=305,845` (VAREQUISTION463 = 550, VATEST70 = 20) |
| Email no longer lands in SSN | `coresamplesv2.patient` 3286031 `patient_ssn=''` (was the PID-19 defect) |
| Nothing else pending | `/outgoing/` empty apart from `archive/`; no BIOINSIGHTS row after 7196 |
| Results not being collected | `/incoming/` holds 153 `.hl7` result files, newest 2609116512 (Sep 11) |

Deliberately NOT in the email (per the 2026-09-24 rule — another party's deliverable never carries our
timeline, and we do not route work through a third party):
- no date, owner name, or commitment for the compendium;
- no request that devcom chase anyone internally at Vibrant or BioInsights.

Open internally, not stated to devcom:
- whether to cancel the $570 test order against JAG (`is_canceled` NULL, no charging transaction);
- JAG's actual EMR-ordering payment method (open since 2026-07-27). The email asks devcom only to confirm
  what IN1-2 is *meant* to say, which is a question about the message they build — cut the paragraph if
  you would rather settle it with JAG first.

---

Hi Olena,

Good news: V00000417.hl7 went through cleanly. We received it on 25 September at 18:30 UTC, it parsed
with no errors, and it created a real order in our production system:

  - Order / requisition:  V00000417
  - Vibrant accession:    2609256344
  - Tests accepted:       VAREQUISTION463 (Gut Zoomer 5.0) and VATEST70 (Vitamin D, 25-OH)

This is the first order that has ever come through the BioInsights connection end to end, so the ordering
side of the integration is now proven: file pickup, provider lookup, test mapping, patient creation and
order creation all work.

Every point from my previous email has been applied correctly. For the record:

  1. The two test codes now resolve to orderable tests.
  2. ORC-12 / OBR-16 are now 1730269200^Balandan^Paola^^^^^^N, so we read the family and given name from
     the right components.
  3. OBR-7 is empty, so the collection time defaults to the time we receive the order instead of a
     backdated value.
  4. The patient email is now in PID-20. I checked the created patient record: the email is no longer
     written into the SSN field, which was the one item that would have corrupted real patient data.

A few fields are still not what they look like, but none of them block anything and none of them are
urgent. I am listing them only so they do not surprise you later:

  - MSH-5 "IN OFFICE" and MSH-6 "LC" are the receiving application and receiving facility. We do not read
    them for this integration. If "IN OFFICE" was meant to describe where the draw happens, tell me and I
    will point you at the field that actually carries it.
  - FASTING / NON-FASTING is in OBR-26. We read OBR-19. Today this changes nothing, because the value has
    no consumer on our side either way.
  - MSH-12 says 2.5 while the integration is configured as 2.3. Not enforced, no action needed.
  - OBR-11 "N" and OBR-15 "0" are not valid values for those fields. Also not read by us.

One thing to confirm, because it is the next gate after the message format: IN1-2 = "C" tells us to bill
the practice rather than the patient. That is what we applied to this order. Please confirm that billing
the practice is what BioInsights intends for these orders; if it is not, that is a one-character change on
your side and I will tell you which value to send.

Please also keep using the test patient for now, and let me know before you run any larger batch. Each
file that parses creates a genuine order in production, so we want to agree on the volume first.

On the compendium: I understand this is still blocking you, and I have passed the request on internally.
The catalogue is owned by another team at Vibrant, so I cannot give you a date for it. What I can tell you
is that it does not block the work you have in front of you: the two codes you are using are correct and
orderable today, so you can continue testing the message format and the order flow with them while the
full catalogue is being prepared.

Separately, one observation from our side. We have been delivering result files to /incoming/ since late
July, and there are now 153 HL7 result files sitting there, the newest from 11 September. None of them
have been collected. If result consumption is part of your scope, that side of the connection has not
started yet — let me know if you would like to pick that up next, or if it belongs to a different team.

Best regards,
Leo
