# VP-17827 - Reply to Prospera (Follow That Patient), round 2: intake used provider ID, ORC-17 not read

> Draft v1, 2026-10-08. Thread: "Including Practice ID in Vibrant order messages". Replies to Tom's 10-08 mail
> (confirmed both points; asked whether intake chose the practice from the provider ID, from what date billing uses
> ORC-17, and whether the trial orders will be re-billed).
> Leo's voice. Not sent. Evidence (raw HL7 of all 9 archived orders, read from the on-prem prod pod) is in
> `storage/short_term_memory/VP-17827.md` (2026-10-08 section).
> Before sending: decide whether to state a go-live date. Internal target only: Xiaoye put VP-17827 in Team Yekai
> Sprint 31 today, due 2026-10-23, no comment. The date and the re-billing belong to Keith, so the draft hands
> both to him instead of promising.

---

**To:** Tom Porter
**Cc:** Robin Mattingly, Keith, Xiaoye Li

Subject: Re: Including Practice ID in Vibrant order messages

Hi Tom,

Thanks for confirming both.

Yes. Our intake currently takes the location from the provider ID and does not read ORC-17. We are changing it to use ORC-17.

Orders from provider 43262 that we booked to 2930 while ORC-17 said otherwise:

| Your order | ORC-17 | Booked to |
|---|---|---|
| FTP3-5 | 36290 | 2930 |
| FTP3-9 | 8003 | 2930 |
| FTP3-10 | 36290 | 2930 |
| FTP3-11 | 8003 | 2930 |
| FTP3-12 | 8003 | 2930 |

Orders from providers set up at a single location (FTP3-4, FTP3-8, FTP13-6) were booked to the location in ORC-17.

Keith, over to you on the go-live date and on re-billing the five orders above.

Thanks,
Leo
