# VP-17827 / VP-17826 - Reply to Prospera (Follow That Patient) on Practice ID in order messages

> Draft v1, 2026-10-07. Thread: "Including Practice ID in Vibrant order messages" (Keith -> Robin/Tom, 10-06; Keith looped in Xiaoye + Leo 10-07).
> Leo's voice. Not sent. Internal evidence and gaps are in `storage/short_term_memory/VP-17827.md` (2026-10-07 section), not here.
> Before sending: fill or drop the blank Provider cells (9 accounts from the 06-22 batch have no name in lis_emr; portal has them).

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

The Practice IDs currently set up for your providers are below. The Vibrant Provider ID is the value you already send in ORC-12.

| Practice ID | Location | Vibrant Provider ID | Provider |
|---|---|---|---|
| 2930 | Next Health | 2797 | Darshan Shah |
| 2930 | Next Health | 26232 | Jeffrey Egler |
| 2930 | Next Health | 43262 | Anna Emanuel |
| 8003 | Next Health | 6263 | Darshan Shah |
| 8003 | Next Health | 26308 | Jeffrey Egler |
| 8003 | Next Health | 43262 | Anna Emanuel |
| 22106 | Next Health | 30528 |  |
| 22106 | Next Health | 43263 |  |
| 22106 | Next Health | 502816 |  |
| 22106 | Next Health | 523148 |  |
| 27533 | Next Health Four Seasons | 25904 | Rowena Nikki Baysa |
| 36290 | Next Health Studio City | 19472 | Darshan Shah |
| 36290 | Next Health Studio City | 25899 | Jeffrey Egler |
| 36290 | Next Health Studio City | 43262 | Anna Emanuel |
| 139948 | Next Health | 34657 | Nathan Byrnes |
| 142676 | Next Health | 38677 | Amanda Perkins |
| 142676 | Next Health | 44149 | Gleb Gendel |
| 143714 | Next Health | 39800 | Carla Winter-Bryant |
| 144164 | Next Health | 40292 | Nicole Krauss |
| 144510 | Next Health Fashion Island | 40660 | Milan Shah |
| 144510 | Next Health Fashion Island | 43262 | Anna Emanuel |
| 145373 | Next Health | 47714 | Casey N Chandler |
| 148164 | Next Health | 44493 | Albert Bales |
| 148164 | Next Health | 48085 | Lindsey Weak |
| 149122 | Next Health | 45492 | Lea Brainerd |
| 149839 | Next Health | 46803 |  |
| 149877 | Next Health | 46332 | Shawna Grant |
| 149877 | Next Health | 47629 | Anne Marie Fombu |
| 149982 | Next Health | 46454 | Amanda Morelli |
| 150053 | Next Health | 46535 |  |
| 151504 | Next Health | 48127 |  |
| 152014 | Next Health | 51471 |  |
| 154338 | Next Health | 51154 |  |

Thanks,
Leo
