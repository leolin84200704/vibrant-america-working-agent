# Reply to JAG — why a "John Doe" BioInsights test order landed in their account, 2026-10-01

Context: JAG wrote to Leo that a lab order + charge for "John doe" (Vitamin D, Gut Zoomer) appeared in their
portal, placed by none of their staff, with no phone/address for kit shipping, and asked why their account is
used to test BioInsights. Leo: list the mapping, reply, ask them for the correct mapping.

Ground truth (prod lis_emr, 2026-10-01): ehr_integrations cms3icsz700010xlgywfuj8do, vendor 46 BioInsights,
customer 30248 / clinic 132493 / NPI 1730269200, FULL_INTEGRATION LIVE, ordering_enabled=1, kit NO_DELIVERY.
Order = devcom test file V00000417.hl7 (hl7_file_input 7196, 2026-09-25) -> accession 2609256344,
emr_sample 6618, order_table 30139923543497260, $570 customerPay, test patient John Doe (patient 3286031).

Open for Leo before sending: (a) greeting/name; (b) the bracketed sentence about the charge — void the test
order first, or leave the sentence out; (c) CC BioInsights (Serdar / Lisa) since the mapping came from them.

---

Hi [name],

The "John Doe" order (accession 2609256344, Vitamin D and Gut Zoomer) is a test order sent by BioInsights.
It came in through the BioInsights EMR connection, which is set up against your account as follows:

  - Office:    JAG Holdings Group, LLC
  - Provider:  30248 (NPI 1730269200)
  - Practice:  132493

This is the mapping BioInsights gave us on 27 July when they asked us to connect their platform to your
office. Any order BioInsights sends under that NPI lands in this account, and their test order was sent as
billed to the practice, which is why you see a charge. No kit ships for it.

[We are voiding the test order on our side.]

If this is not the provider and practice BioInsights should be ordering under, please send me the correct
ones — provider name and NPI, and the practice they belong to — and we will move the connection before
anything else comes through.

Best regards,
Leo
