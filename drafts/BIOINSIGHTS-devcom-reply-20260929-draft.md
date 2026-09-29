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
| IN1-2 mapping | `parser.service.ts` L653-657 on origin/main: `chargeMethodFromIn1` reads IN1-2 CE.1 only; `'C'` -> `CUSTOMER_PAY`, everything else and a missing IN1 -> `PATIENT_PAY_LATER`. No other ChargeMethod value is reachable from HL7. L856: `PATIENT_PAY_LATER` sets `send_email=true` (the patient payment link) |

Compendium handling (Leo, 2026-09-29): do NOT answer on Zhenhe's behalf. The email hands the request to
its owner by adding him to the thread and asking him directly, in front of Olena. Still no date and no
commitment in our voice — the ask, and the answer, are his.
- ACTION FOR LEO: add Zhenhe Zhang's address to the To/Cc line. Not recorded in memory, so not filled in here.

Also not in the email: no request that devcom chase anyone internally at Vibrant or BioInsights.

OPTIONAL — cut if you want this to answer only what was asked (the "vendor email" rule in
long-term-memory/leo-working-rules.md): the paragraph asking them not to run a larger batch yet, and the
closing paragraph about the 153 uncollected result files. Both are true and both are ours to raise, but
neither was asked in this email.

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

One thing to confirm, because it is the next gate after the message format: IN1-2 decides who pays, and we
read only its first component. There are exactly two outcomes:

  - IN1-2 = "C"                          -> the practice is billed (customerPay)
  - anything else, or no IN1 segment     -> the patient is billed (patientPayLater), and we email the
                                            patient a payment link

You are sending "C", so order V00000417 was booked as billed to JAG Holdings Group. Please confirm that is
what BioInsights intends. If you want the patient to pay instead, send any other value in IN1-2 — "P" is
the conventional one — or leave the IN1 segment out entirely; both take the same path.

Please also keep using the test patient for now, and let me know before you run any larger batch. Each
file that parses creates a genuine order in production, so we want to agree on the volume first.

On the compendium: I am adding Zhenhe Zhang to this thread, who owns the test compendium on our side.

Zhenhe, Olena at Devcom is building the BioInsights HL7 integration and needs the current test compendium
with CPT and LOINC codes. Could you send it to her directly, or tell her what you need from her to
release it?

Separately, one observation from our side. We have been delivering result files to /incoming/ since late
July, and there are now 153 HL7 result files sitting there, the newest from 11 September. None of them
have been collected. If result consumption is part of your scope, that side of the connection has not
started yet — let me know if you would like to pick that up next, or if it belongs to a different team.

Best regards,
Leo
