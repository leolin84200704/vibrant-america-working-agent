---
date: 2026-11-05
tickets: [VP-18842, VP-17411]
tags: [emr-v2, charging, customerPay, place-order-api, regression, plessen]
distilled: true
---
# VP-18842 follow-up: customerPay charge account + unpaid-order fallback

Leo pasted hl7_file_input 7505 (Plessen) and asked why it failed. Two layers: emr-v2 charged every shared
card as account_type=customer while charging resolves the Stripe customer from the account (clinic card ->
provider Stripe customer -> rejected), and the 11-04 Place Order API switch turned that long-standing payment
failure into a blocked order (order-management rejects unpaid customerPay; the processor comment assumed it
would flag instead). Leo: "兩個都做" -> PR #531 (owner-tagged candidates, clinic-account charge, legacy
fallback for unpaid customerPay) -> staging E2E (2263 legacy fallback, 2264 card walk) -> release #532 merged
-> prod fc3b96a -> 7505 re-placed as sample 2666162. Remaining: stripe server-to-server charges still end in
requires_confirmation (charging, VP-17411 2a) so Plessen stays "ship unpaid, collect manually" until charging
supports off-session confirm.

Lessons: (1) a comment claiming a downstream service "flags" something is a claim about another repo - read
that repo (order_helper.go) before shipping; (2) when a charge fails with an identity error, check which
account the downstream derives identity from, not the token you sent; (3) staging has one usable
provider/clinic pair with a clinic card (999997@10136) and none with only a clinic card - the clinic-account
path had to be proven with a direct charging probe.
