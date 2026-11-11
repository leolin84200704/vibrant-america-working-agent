---
id: 2026-11-11-vp18465-cloud-local-proxy-scale-to-zero
type: journal
date: 2026-11-11
tickets: [VP-18465]
tags: [cloud-local-proxy, scale-to-zero, aks, on-prem, retirement, prod-change]
distilled: false
---
# VP-18465: cloud-local-proxy scaled to zero on both clusters

Leo approved Phase 1. Re-ran the gate live instead of trusting the 11-10 VP-18464 closeout numbers: a fresh
probe was seen in the AKS pod log, in Datadog (about 2 min late, which first looked like a dead logger), in the
on-prem capture and in the on-prem pod logs. So every observer was alive, and all four still held only probe lines.
Preserved pod logs, objects and ConfigMaps for both clusters to ~/src/credential before touching anything,
then scaled at 20:11:35Z (AKS) / 20:11:39Z (on-prem). Probes went 200 -> 503 on all four fronts.

Surprise: AKS -st had already been 0/0 since about 10-25 07:19Z, by someone unknown. It is the target state,
so I noted it rather than chasing it.

Gap: I did not probe vw-page (shares the on-prem ingress) before scaling; after, it answers 404 from its own
app on `/`, pods untouched. A scale cannot reach it, but a before/after probe of the neighbour is cheap and
should be in the pre-steps.

Lesson: when Datadog shows no probe line right after a probe, check the pod log before calling the observer
dead; ingestion lag is minutes.
