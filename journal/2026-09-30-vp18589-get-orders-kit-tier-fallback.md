---
date: 2026-09-30
tickets: [VP-18589, VP-17760, VP-18030]
tags: [partner-api, get-orders, shipping, kit-status, staging, docs-drift]
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
