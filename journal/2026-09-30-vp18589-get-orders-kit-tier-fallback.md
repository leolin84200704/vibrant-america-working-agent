---
date: 2026-09-30
tickets: [VP-18589, VP-17760, VP-18030]
tags: [partner-api, get-orders, shipping, kit-status, staging, docs-drift]
distilled: true
distilled_on: 2026-10-06  # 10-02 body; the 2026-10-05 appended section distilled 10-06 -> emr-integration / leo-working-rules / patterns
---
# 2026-09-30 — GET /orders list vs lookup disagreement (VP-18589)

## Trigger
Leo pasted an integrator's message (via Chris Wu): sandbox `GET /orders?placerId=`
always `kit: null`, three W2W- orders where list said kit_delivered and lookup said
placed, and "is there any status for delivery failed / lost / return failed / sample
rejected". Asked 「這個API問題是什麼？」, then 「重點是什麼」, 「第三點是emr的問題嗎」,
then 「全部按照文檔先做完，然後給我回覆客戶的comment」.

## What I explored, in order
1. Memory grep → VP-17760 (lookup) / VP-18030 (list) STMs; read both derivations on
   origin/main (main checkout sits on VP-18085's branch, so `git show origin/main:`
   was the honest read path until the worktree existed).
2. Datadog patterns 09-24..09-30: staging 334× shipping client not initialized, 129×
   sample not found in core; prod 2× `kit_delivery_exception` unmapped (09-29).
3. mintlify page fetched: still lists kit.carrier/shippedAt/deliveredAt,
   report.availableAt, exceptions.raisedAt, report.status `cancelled`. VP-17760 Jira
   comments 183880/183942 (L4-verified) dropped exactly those five on 08-13 → the DOC
   is stale, not the code. This reframed 「按照文檔做」: only the status derivation is
   doc-conformant work; the fields are an api-product doc fix.
4. Shipping vocabulary: transformer (LIS-transformer getPatient.service.ts) handles
   8 raw values; emr-v2 knew 6. DELIVERY_EXCEPTION / VOIDED_SHIPMENT were the gap.
   Core `order_kit_status` has 7 values; list ladder had 6.
5. Staging reachability from the emr-v2 staging pod: on-prem :31995 (base-report's
   "STAGING" shipping addr) and :31865 ECONNREFUSED; cloud
   lis-shipping-service-grpc.shipping.svc.cluster.local:63142 OPEN but prod data.
   → sandbox kit flow needs a shipping-team staging instance; not a config flip.

## Decisions
- Fallback to core only when shipping is null (reachable shipping stays authoritative).
- `kit` block stays null when degraded — kept the documented "null = unavailable"
  meaning instead of synthesizing a block with no tracking number.
- DELIVERY_EXCEPTION → kit_shipped / sample_in_transit (contract has no exception slot).
- Filed VP-18589 as Task (own-scope rule), linked Relates VP-17760, assigned Leo.

## Ruled out
- Pointing staging at the cloud shipping svc (prod kits for staging sample ids).
- Implementing carrier/shippedAt/deliveredAt from the tracking URL / po_create_time
  (VP-17760 already rejected URL pattern-matching; no delivered timestamp exists).

## Output
PR #444 draft → staging, head 9826235. Customer reply drafted for Leo (engineer's
view: who owns what, why it is missing), not sent.

## Post-merge (same day)
Leo merged #444 → staging at 22:36Z; image :288bb1e live 22:46Z. Old pod reproduced
the bug on 4 rows (kit_delivered vs placed) seconds before it was terminated; new pod:
119/119 kit-tier rows agree across 6 customers. Learned the integrator (customer 50687)
has since cancelled all 40 of its sandbox orders, so their own placerIds can no longer
demonstrate the fix — the proof is on other customers' rows.
Two pre-existing lookup-vs-list asymmetries surfaced by the sweep (report-service signal
only in lookup; core order_cancel_time only in list). Not touched — one-PR-one-scope.
Leo's sequencing: Chris fixes the doc first, customer reply after.

## Evening: VP-18593 (carrier / shippedAt / deliveredAt) — same day
Leo challenged the 08-13 "no upstream has them" premise. LIS-Shipping read-only review:
FedEx EDI → Service Bus → shipping tables; pickup_time already on the kit RPC (our
proto copy was 4 fields, proto-loader dropped field 5); carrier + delivery scan on
GetTrackingDetails in a SECOND proto file (shipping-protos/shipping-service.proto).
I first proposed asking shipping for a field — Leo: 「不要改shipping 的東西」 — and the
existing RPC made that moot. Lesson: enumerate the server's @GrpcMethod handlers before
saying "the RPC does not expose X". Both PRs merged + promoted; verified on the prod
pod with the deployed build against live shipping. Prod has no real integrator orders
yet, so the customer's own orders cannot be shown — the proof is on internal samples.

## Night: VP-18595 / VP-18596 (Leo: 「直接做」)
Two branches off staging, two PRs (#448, #449), both merged by Leo within the hour.
Staging sweep after 2ac6b05: the cancel-timestamp divergence is gone (3 left, all
report-service-only). The return-label rule cannot fire on staging; its proof is the
six-case unit matrix plus a prod check after promotion. Leo had already set both
tickets to Done before the code existed — left as-is, noted.

## 2026-10-05: sandbox seed request (Chris + Yekai) and Leo's reply
> distilled 2026-10-06 (dream) -> emr-integration.md 2026-10-06 sandbox recipe, leo-working-rules.md 10-03→10-06, patterns.md 2026-10-06.
Integrator wants 11 sandbox orders in target states. Mapped each to core/report data;
kit block impossible without shipping. Leo wrote the Slack reply himself from my draft
and asked me to remember how he phrased it — verbatim in STM
SANDBOX-SEED-W2W-20261005 § User Feedback, with the deltas vs my draft. Also learned
(the hard way) that "we" do call FedEx Track directly: LIS-transformer getFedx and
LIS-Shipping kitTrack, consul shipping secret. in_transit is a shipping-vocabulary
gap, not a FedEx one; emr-v2 direct FedEx tracking is an open option, not decided.
