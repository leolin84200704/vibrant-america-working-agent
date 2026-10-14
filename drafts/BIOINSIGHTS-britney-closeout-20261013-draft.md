# Closeout confirmation to Britney (JAG separation) -- updated 2026-10-14

Reply-all target: Zhenhe's 2026-10-14 21:26Z "@Leo Canceled" mail (thread To: Leo, Britney, Keith, Kristina, Mingxi).
Outlook draft created 2026-10-14 (final form, no placeholders).

## For Leo -- DO NOT SEND until item 1 is true
- Item 1 says the John Doe patient record "has been deactivated". As of 2026-10-14 ~22:00Z it is NOT:
  coresamplesv2.patient 3286031 (John Doe, customer 30248, created 2026-09-22 from devcom file V00000416) still isActive=1.
  Agent has no write path; ask Mingxi (Slack, Chinese) to deactivate it first, then send.
- Verified 2026-10-14 (lisportalprod2 ro):
  - lis_re.order_table 30139923543497260 / sample 2642225: is_canceled=1.
  - lis_charging.transactions 447178 (charge $570, card ****8527, stax, 09-25) and NEW 1008956 type=refund $570 same card,
    created 2026-10-14 16:32Z, status 1. Original row still refunded=0 (flag not updated by the refund flow; refund row is the evidence).
    Zhenhe 21:16Z: "The order has been canceled, and the refund process has been initiated."
- BioInsights has not replied to Leo's 10-13 19:09Z provider-confirmation mail (no mail from bioinsights.com or devcom since).
  Item 3's "will forward that confirmation" is still an open promise.

---

Hi Britney,

Confirming the four items:

1. Patient information: the only patient record that came through the BioInsights connection is the "John Doe" test record.
   The 25 September order was cancelled on 14 October and the test patient record has been deactivated in JAG's account.
   No other patient data entered JAG's account from BioInsights.
2. Billing: the $570 charge was refunded to the card on 14 October. Depending on the card issuer it can take a few business days to show.
3. BioInsights-related information and access: JAG's office was removed from the BioInsights connection on 13 October. Result files
   for JAG patients that our system had delivered to BioInsights' SFTP folder between 29 July and 13 October were deleted by us on
   13 October. We have asked BioInsights to confirm in writing that nothing was retained on their side and will forward that confirmation.
4. Nothing else links the two: BioInsights' own account (Travis Bond, MD) has no connection to JAG's account or practice, and JAG's
   existing integration is unchanged.

Best regards,
Leo
