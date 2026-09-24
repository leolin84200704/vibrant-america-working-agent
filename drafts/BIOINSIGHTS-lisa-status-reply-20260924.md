# Reply to Lisa Bond (BioInsights CPO) — integration status, 2026-09-24

Context: Lisa (CPO) asked Britney + Leo where the integration stands and what is holding it up,
forwarding Leo's 09-23 field audit of V00000416.hl7 and Olena's compendium chaser.

Leo's scope instruction: answer only the engineering wait (a correct HL7 file). Do not vouch for
anyone else's deliverable — no promise about the test catalog (Zhenhe's item), no asking Lisa to
chase JAG on billing or to nudge devcom.

---

**To:** Lisa Bond, Britney Little
**Cc:** Travis Bond, Olena Momotko
**Subject:** Re: Vibrant Wellness & Bioinsights

Hi Lisa,

On the engineering side, the integration is in HL7 order-file testing, and it is waiting on one
thing: a corrected test file from Devcom.

We reviewed their latest file (V00000416.hl7) on Sep 23 and replied the same day with the full list
of what needs to be corrected — the blocking item is the test codes, and we included every other
issue we found in the file so it can all be fixed in one pass. That reply is with Olena.

The corrected file needs to go out under a new file name and a new MSH-10 message control ID; we
de-duplicate by file name, so V00000416.hl7 will not be reprocessed even after the corrections. We
review each file the day it lands.

Best regards,
Leo
