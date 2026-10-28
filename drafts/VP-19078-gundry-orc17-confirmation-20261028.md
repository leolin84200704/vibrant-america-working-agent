# VP-19078 — drafts (not posted)

## Jira comment on VP-19078 (Leo's account), for Junjie to relay

@Junjie Lin Gundry's updated spec and sample ORC are correct.

- ORC-17.1 is the field we read for the practice ID; 32351 parses as expected.
- Every Gundry provider we have (16) is set up at practice 32351, and every Gundry order in the last 12 months came in under Dr. Gundry's NPI, so a fixed 32351 is right for them.
- Nothing changes for them before go-live: an order without ORC-17 is handled exactly as today.

Please confirm the format to Rob and ask for the go-live date. We turn the field on for Gundry on that date and check the first live orders.

## Text Junjie can send to Rob Murray

Confirmed. ORC-17.1 = 32351 is the right value for every Gundry provider, and the sample ORC you sent parses correctly on our side. Please let us know the go-live date; until then orders without the field keep working as they do today.
