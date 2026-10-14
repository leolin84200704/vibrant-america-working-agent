---
id: INCIDENT-20261013-bioinsights-jag-crossmap
type: stm
category: emr_integration
status: active
base_weight: 1.0
created: 2026-10-13
updated: '2026-10-13'
links:
- BETA-E2E-20260729
- BIOINSIGHTS-SFTP-KEY
- BIOINSIGHTS-onboarding
- FHIR-ONDEMAND-RESULT
- HL7-NPI-PRACTICE-MATCH-20260820
- HL7FAIL-20260729-PLESSEN
- HL7FAIL-20260730-TURNPAUGH
- HL7FAIL-20260903-EVERSPAN
- INCIDENT-20260808-critical-result-tnp
- INCIDENT-20260817-onprem-stale-deploy
- INCIDENT-2604156666
- LBS-1762
- LBS-1773
- LBS-1784
- LBS-1785
- LBS-1799
- LBS-1828
- LBS-1833
- LIS-7716
- NEXTECH-onboarding
- PH-847
- QH-1660
- QH-2257
- QH-2577
- QH-3752
- QH-4350
- QH-4352
- QH-4608
- QH-5840
- QUARANTINE-ADMIN-API-GAP-20260924
- RESULTCHECK-20260819-RCODE-2608186060
- VEJO-DELETION-20260804
- VP-16166
- VP-16934
- VP-16968
- VP-16987
- VP-17344
- VP-17460
- VP-17466
- VP-17475
- VP-17493
- VP-17497
- VP-17499
- VP-17503
- VP-17517
- VP-17524
- VP-17537
- VP-17538
- VP-17539
- VP-17544
- VP-17584
- VP-17589
- VP-17591
- VP-17628
- VP-17631
- VP-17685
- VP-17686
- VP-17691
- VP-17715
- VP-17734
- VP-17748
- VP-17752
- VP-17760
- VP-17810
- VP-17812
- VP-17827
- VP-17914
- VP-18030
- VP-18034
- VP-18055
- VP-18066
- VP-18080
- VP-18085
- VP-18086
- VP-18138
- VP-18185
- VP-18194
- VP-18243
- VP-18270
- VP-18288
- VP-18372
- VP-18402
- VP-18404
- VP-18593
- VP-18664
- VP-18665
- VP-18666
- VP-18704
- VP-18714
- VP-18755
- VP-18824
- emr-integration
- fhir-api
- leo-working-rules
tags:
- incident
- bioinsights
- jag
- phi-disclosure
- practice-mapping
- retrospective
summary: 'Retrospective (Leo: "這是嚴重的錯誤，請你檢討"). 07-27 the agent attached JAG Holdings
  (customer 30248 / clinic 132493, sent by Britney in the Canvas Medical HTTP(S) thread)
  to the BioInsights SFTP vendor as its practice. Consequences over 78 days: 200 JAG
  patient result files double-delivered to an unrelated third party SFTP (PHI disclosure);
  devcom test order V00000417 booked and charged $570 to JAG (customerPay); 12 days
  between JAG complaint (10-01) and containment (10-13). Memory recorded the source
  as "Serdar email" which never existed; two L4 checks verified the DB row instead
  of the originating email. Eight concrete rule changes listed under Lessons.'
score: 1.275
---

# INCIDENT 2026-10-13: BioInsights vendor row carried JAG's practice for 78 days

## What happened (plain)
A clinic (JAG Holdings Group, customer 30248) that has nothing to do with BioInsights was registered as
BioInsights' practice on 2026-07-27. Because of that, (a) every result for JAG's real patients was also
copied to BioInsights' SFTP server for two and a half months (200 files, 2026-07-29 .. 2026-10-13 01:31Z),
(b) BioInsights' developer was told to use JAG's NPI for test files, so a test order was placed in JAG's
account and the practice was charged $570, and (c) JAG discovered it themselves on 10-01 and nothing
was switched off until 10-13.

## Error chain (each link had a chance to stop it)
1. **07-27 root cause - wrong source for the practice scope.** Britney's "Integration Details: JAG ..."
   email arrived in the Zendesk thread about Canvas Medical wanting HTTP(S) (subject "[Vibrant Wellness]
   Re: Integration", CC payton.smith@canvasmedical.com). The agent was waiting that week for BioInsights
   to name a practice and treated the first "integration details" email that arrived as that answer.
   Signals ignored: the thread subject and CC were Canvas, not BioInsights; the request was HTTP(S), not
   SFTP; the BioInsights thread had never mentioned a practice; the STM itself wrote "BioInsights appears
   to ride on Canvas Medical's EMR platform" marked unverified and then went LIVE anyway.
2. **07-29 second chance missed.** Support (Terry) replied in the same thread calling it "the Canvas
   integration" and asked whether to disconnect P2P. Nobody answered; the contradiction was not noticed.
3. **07-27 went LIVE with result_enabled=1 on an unverified mapping.** The STM even logged "DOUBLE RESULT
   DELIVERY flag" and left it to a later decision. Enabling result push is enabling PHI egress; it was
   done on an assumption.
4. **Memory pollution.** STM recorded the mapping as "exactly what BioInsights (Serdar, 07-27) gave us".
   Serdar never sent such an email. From then on every reasoning step started from a false premise.
5. **09-15 / 09-18 propagated the error outward.** We instructed devcom to put NPI 1730269200 (JAG) in
   ORC-12, i.e. told a third-party developer to send test traffic into a real customer's account.
6. **09-18 and 09-29 evidence of the PHI leak was seen and misread.** "/incoming/ holds ~150 (then 153)
   result files for customer 30248 that the vendor has never picked up" was logged twice as "vendor not
   consuming results". The right question was "why is BioInsights receiving JAG's patient results at all".
7. **09-23 / 09-29 the billing risk was written down and not acted on.** The field audit said IN1-2=C bills
   the practice; 09-29 said "JAG has a live $570 test order ... Decision needed from Leo". A reversible
   stop (ordering_enabled=0) was available and was not proposed as the default.
8. **10-01 complaint -> 10-13 containment: 12 days.** The 10-01 draft still said "the mapping BioInsights
   gave us" (not sent, factually wrong). Pausing the row was deferred to Leo instead of done. After Leo's
   10-02 "done", prod was not re-checked. 47 more JAG result files went out in October.
9. **10-01 and 10-13 "L4 verification" verified the wrong object.** Both checks re-read the ehr_integrations
   row (which the agent itself had written from the bad premise) and never re-read the originating email.
   Britney's "I see that you all mentioned them first" is what forced the Outlook search.
10. **10-13 execution errors.** Britney's reply said "Removing JAG" 80 s before the prod row changed
    (sequence reversed: change prod, then send). The bracketed placeholder "[Voiding the 25 September test
    order and the charge.]" went out in the sent mail. The Slack message to Mingxi went in English and
    without Leo's review.

## Impact
- PHI: 200 result files for JAG patients delivered to BioInsights' SFTP (deleted 10-13, vendor-side
  retention not yet confirmed in writing). Needs a compliance / privacy-officer assessment, not only an
  engineering closeout -- flagged to Leo.
- Billing: lis_re.order_table 30139923543497260 (sample 2642225, accession 2609256344) $570 customerPay,
  lis_charging.transactions 447178. Reversal handed to Mingxi 10-13.
- Relationship: JAG + Vibrant Wellness CAM (Britney) + Director of Sales (Kristina) escalated over 12 days
  without an answer.
- BioInsights onboarding: 2.5 months of "progress" built on a row that never belonged to them; real
  onboarding restarts when they name a provider.

## Lessons (candidate rules for dream -> emr-integration.md / leo-working-rules.md)
- **R1 Scope source is thread-bound.** Before any ehr_integrations INSERT, the STM must cite the originating
  message (Outlook id, sender, subject) and the sender's domain must be the vendor or the practice itself.
  An "integration details" mail in another thread is not scope for the onboarding in flight.
- **R2 Unverified mapping never goes LIVE, and never gets result_enabled=1.** Result push is PHI egress.
  Use PENDING/APPROVED until the practice-vendor relationship is confirmed by the practice or the vendor.
- **R3 No real customer NPI for vendor testing.** A test instruction to a vendor must point at a test
  customer, or at a practice that has agreed in writing; never when IN1-2=C (practice billed).
- **R4 Unexpected files on a vendor SFTP are a "should this be here" question first,** not a "why is the
  vendor not consuming" note. Result files for a customer on a vendor's server = check the mapping.
- **R5 Complaint = same-day reversible stop.** "There is something in my account that is not mine" ->
  set ordering_enabled=0 / status off the LIVE path that day, then investigate. Do not route a reversible
  containment through "Leo decides".
- **R6 Verify provenance against the source, not against our own writes.** A question of "who told us X"
  is answered by re-reading the message, never by reading the DB row we created from it.
- **R7 No placeholders inside the outgoing body.** Open decisions live in the "for Leo" section of the
  drafts file, not as [brackets] in the Outlook draft.
- **R8 Prod first, then the email that claims it; every outgoing message is shown to Leo before sending;
  Mingxi in short informal Chinese** (Leo, 2026-10-13).

## Status 2026-10-13
- R1/R2/R3 are now enforced-by: lis-prod-change-gate Gate 1b (PR #57, merged by Leo 23:55Z, 02f8fe6).
Row cms3icsz700010xlgywfuj8do REJECTED (18:31:10Z, history 218); 200 files deleted; order cancel + charge
reversal with Mingxi; BioInsights provider confirmation draft pending Leo; closeout to Britney pre-drafted.
