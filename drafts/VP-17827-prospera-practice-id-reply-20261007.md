# VP-17827 / VP-17826 - Reply to Prospera (Follow That Patient) on Practice ID in order messages

> Draft v1, 2026-10-07. Thread: "Including Practice ID in Vibrant order messages" (Keith -> Robin/Tom, 10-06; Keith looped in Xiaoye + Leo 10-07).
> Leo's voice. Not sent. Internal evidence and gaps are in `storage/short_term_memory/VP-17827.md` (2026-10-07 section), not here.
> Attachment: `drafts/VP-17827-prospera-practice-ids-20261007.csv` (4 columns, outward-facing). Internal version with NPI / flags / source: `reference/followthatpatient-practice-ids-20261007.csv`.
> Before sending: fill or drop the blank Provider cells in the CSV (9 accounts from the 06-22 batch have no name in lis_emr; portal has them).

---

**To:** Tom Porter
**Cc:** Robin Mattingly, Keith, Xiaoye Li

Subject: Re: Including Practice ID in Vibrant order messages

Hi Tom,

Good news: your order messages already carry our Practice ID. On the orders we have received from Follow That Patient, MSH-6 (Receiving Facility) and ORC-17 (Entering Organization) both hold the Vibrant Practice ID of the location the order was placed from, for example 36290 for Studio City. So there is no new field to add.

Two things to confirm on your side:

1. Both fields always carry the Vibrant Practice ID of the ordering location, for every location, not only the ones that have ordered so far.
2. The value follows the location, not the provider. When a provider orders from a location other than their usual one, the field should show that location's Practice ID.

If either is not the case, ORC-17 is the field we would like it in.

The Practice IDs currently set up for your providers are in the attached CSV. The Vibrant Provider ID is the value you already send in ORC-12.

Thanks,
Leo
