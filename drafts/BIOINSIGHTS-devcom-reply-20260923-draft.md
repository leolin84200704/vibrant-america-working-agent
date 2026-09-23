Subject: Re: Integration with Vibrant Wellness - review of V00000416.hl7

Hi Olena,

We picked up V00000416.hl7 and it got further than the previous file: the ORC-12 NPI
is correct now and the order resolved to the right practice (JAG Holdings Group).
Thank you for the fix.

It stopped at the next gate, the test codes. Below is everything we found in the
file, not just the blocking item, so you can correct it all in one pass instead of
one round trip per issue.

1) Test codes - BLOCKING
Both codes exist in our catalog, but they identify different tests than the names
you sent, and neither one is orderable:
  - VAREQUISTION279 -> "Gut Zoomer 4.0" in our catalog (not "Gut Zoomer 3.0"), not orderable
  - VATEST2270      -> "Copper Serum" (not "Vitamin D"), not orderable
Please use instead:
  - Gut Zoomer -> VAREQUISTION463  (Gut Zoomer 5.0)
  - Vitamin D  -> VATEST70         (Vitamin D, 25-OH)
The mismatch between the codes and the names suggests the test list you are working
from is not our current one. We will send you the current catalog so you can map the
full menu rather than these two items; please order only from that list.

2) Patient email is in the wrong field - PID-19 -> PID-20
We read the patient email from PID-20.1. PID-19 is the SSN field, so
"john_doe@grr.la" as sent would be stored as the patient's SSN and the email address
would be lost. Please move the email to PID-20.1 and leave PID-19 empty unless you
are actually sending an SSN.

3) ORC-12 / OBR-16 have one extra empty component
You are sending:
    1730269200^^Balandan^Paola^^^^^N
In XCN, component 2 is the family name and component 3 the given name, so with the
extra empty component we read family name = "" and given name = "Balandan". (This is
also why the rejection on your first file read "Balandan".) Please send:
    1730269200^Balandan^Paola^^^^^^N
Everything from component 2 on needs to shift left by one. Could you also confirm
what the trailing "N" is meant to be? It currently lands in XCN.9 (assigning
authority), which is probably not the intent.

4) OBR-7 collection date
OBR-7 is 202609141151, seven days before the message timestamp. We take OBR-7
verbatim as the sample collection time. For a new order please send the intended
collection date, or leave OBR-7 empty and we will default to the time we receive the
file.

5) Fasting status
FASTING / NON-FASTING is in OBR-26. We read fasting status from OBR-19; OBR-26 is
ignored.

6) Patient identifier
We do not use the PID-3 UUID for patient matching. Patients are matched within the
practice on first name, last name, gender and date of birth. If you want to carry
your own patient identifier through, send it in PID-2.

7) Diagnosis codes - no change needed
We collect all DG1 segments for the order as a whole, so the per-OBR grouping
(K59.00 / R19.7 with the Gut Zoomer, E55.9 with the Vitamin D) is not preserved on
our side. Flagging it only so you know it is expected behavior, not a defect.

8) MSH-5 / MSH-6
These are currently "IN OFFICE" and "LC". Those fields are receiving application and
receiving facility; we ignore them. If "IN OFFICE" is meant to say where the sample
is drawn, that needs a different mechanism - let us know what you intend and we will
tell you where it belongs.

9) Resending
We de-duplicate by file name, so V00000416.hl7 will not be reprocessed even after you
correct it. Please resend under a NEW file name, and use a new MSH-10 message control
id as well.

One more thing to settle in parallel: IN1-2 is "C", which we read as "bill the
practice". Once the test codes are right, that is the next thing the order is checked
against, so please confirm with JAG that billing the practice is what they want.

Best regards,
Leo

---------------------------------------------------------------------------
OPTIONAL PARAGRAPH (Leo's call - the unpicked results on the SFTP server).
Drop it in if you want to raise it in the same thread:

Separately, on the results side: there are roughly 150 result files sitting in
/incoming/ dated from 2026-07-29 through today that have not been picked up. Could
you confirm whether result retrieval is in scope for your current work, and when you
expect to start consuming that folder?
