---
date: 2026-11-04
ticket: VP-19171
type: journal
tags: [emr-v2, bullmq, sidecar-redis, rollout, lost-jobs, cerbo, causenta, orphan-requeue]
related: [VP-19128]
distilled: true
---

# VP-19171: a Causenta result missing in Cerbo traced to jobs lost on redeploy

## What happened
- The ticket said provider 8104 had no Cerbo integration. Wrong on both counts: the three samples are customer 8105 (Kristy Anderson), and both 8104 and 8105 are LIVE MDHQ. Two of the three had already been TRANSMITTED (09-30, 10-30).
- The third, 2637758 (2609186161), had been PENDING since 2026-10-19 19:36Z. The emr-v2 prod rollout at 19:38Z (#487) killed the pod and its sidecar Redis, and the BullMQ job went with them. The 10-20 03:44Z rollout (#491) did the same. 22 listener rows lost; 19 samples still owed.
- Repushed 2637758 via in-pod gRPC (MDHQ + PRAXISEMR both owed, so the fan-out was correct). Jira comment to Zhenhe approved.
- Leo: "don't let a redeploy drop reports again". PR #526 adds ResultOrphanRequeueService, merged to staging 419b360. Release PR #527 is waiting for Leo.

## Reasoning worth keeping
- The DB row is the durable record of "owed"; Redis is not. Reconcile the two (row unfinished + job missing) instead of making Redis durable. A persistent Redis still loses jobs when Redis itself is replaced.
- Every guard exists against a duplicate send: own pipeline_location (each cluster has its own Redis), a newer TRANSMITTED row, a requeue cap, and a boot delay so the new pod does not judge the old pod's in-flight jobs during a rolling update.
- Staging AKS is POD_ROLE=web, so a pusher-only feature cannot run there. The real test was a prod-pod dry run: compiled code from the staging image, real DB and Redis reads, writes stubbed. It reproduced exactly the 12 lost cloud rows and skipped the resent ones.
- Correction: my first count ("16 others") missed rows that were killed mid-run (GENERATING). Count by the sweep's own predicate, not by generation_status=PENDING.

## Open
- Backlog of 19 samples (12 cloud, 7 onprem) not resent.
- On-prem pusher count is unverified; the design assumes one per location.
- The separate Jira ticket Leo asked for was not created (no create tool in that session).
