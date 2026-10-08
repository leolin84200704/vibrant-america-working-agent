# VP-17827 - Reply to Prospera (Follow That Patient), round 2: intake used provider ID; ORC-17 now used

> Final draft, 2026-10-08 (supersedes v1 of the same day). Thread: "Including Practice ID in Vibrant order messages".
> Replies to Tom's 10-08 mail. Leo's voice. Not sent.
> Our side: fix merged to staging and verified (PR #468); production release is PR #469 (Leo merges). The go-live
> date and the re-billing of the five orders belong to Keith, so the draft hands both to him instead of promising.

---

**To:** Tom Porter
**Cc:** Robin Mattingly, Keith, Xiaoye Li

Subject: Re: Including Practice ID in Vibrant order messages

Hi Tom,

Thanks for confirming both.

Yes. Our intake took the location from the provider ID and did not read ORC-17. That is fixed on our side: from our next production release, the order is booked to the location in ORC-17, and an order whose ORC-17 is a location the provider is not set up at is held rather than booked elsewhere.

Orders from provider 43262 that we booked to 2930 while ORC-17 said otherwise:

| Your order | ORC-17 | Booked to |
|---|---|---|
| FTP3-5 | 36290 | 2930 |
| FTP3-9 | 8003 | 2930 |
| FTP3-10 | 36290 | 2930 |
| FTP3-11 | 8003 | 2930 |
| FTP3-12 | 8003 | 2930 |

Orders from providers set up at a single location (FTP3-4, FTP3-8, FTP13-6) were booked to the location in ORC-17.

Keith, over to you on the release date and on re-billing the five orders above.

Thanks,
Leo
