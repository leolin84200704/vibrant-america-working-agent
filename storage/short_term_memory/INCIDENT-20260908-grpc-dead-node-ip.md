---
id: INCIDENT-20260908-grpc-dead-node-ip
title: emr-v2 result generation outage — every GRPC_*_CLOUD_HOST / GRPC_V2_*_HOST
  pointed at a recycled AKS node IP (10.224.0.199); repointed to 10.224.0.10, pods
  restarted, 58 pushes re-driven
category: technical
status: resolved
created: 2026-09-08
updated: '2026-09-11'
tags:
- incident
- emr-v2
- grpc
- aks
- node-ip
- configmap
- result-generation
- coresamples-v2
related:
- VP-18055
- VP-18095
- INCIDENT-20260518
- INCIDENT-20260817-onprem-stale-deploy
links:
- INCIDENT-20260518
- INCIDENT-20260910-emr-v2-di-crashloop
- VP-17217
- VP-17312
score: 0.1575
---

# INCIDENT 2026-09-08 — result pushes failing: gRPC targets pointed at a dead AKS node IP

## Detection
- Found while live-checking the PR #401 deploy (17:33Z): all 22 result pushes created after the deploy were
  GENERATION_ERROR with `14 UNAVAILABLE ... connect ETIMEDOUT 10.224.0.199:32100`. NOT caused by #401:
  rtr errors on 10.224.0.199 start 2026-09-06 04:48Z, 6/6 failed 09-07 21h, 26/69 failed 09-07 23h,
  100% from 09-08 17h. Both prod pods (AKS + on-prem) affected.

## Root cause
- `10.224.0.199` was an AKS node IP used as the NodePort entry for three services: lis-core v1 gRPC
  (`lis-core-grpc-service` 30276), lis-test-connect (30600), coresamples-v2 (`lis-coresamples-v2-service-nodeport`
  32100 → 8084). The node no longer exists (current node hostIPs: 10.224.0.10 systemonly, 10.224.2.184 /
  10.224.0.244 agentpool, 10.224.1.215 / .1.115 / .0.145 / .1.84 userpool; az finds no NIC with .0.199).
- The IP is hard-coded in 8 keys (`GRPC_{CUSTOMER,PATIENT,SAMPLE,TEST_RESULT,REFERENCE_RANGE}_CLOUD_HOST`,
  `GRPC_V2_{CUSTOMER,PATIENT,SAMPLE}_HOST`) in ALL SIX emr-v2 ConfigMaps (AKS ns emr-v2 ×2, AKS ns default ×2 =
  the copies Jenkins fetches and applies to both clusters on every deploy, on-prem ns default ×2), plus the code
  defaults in `src/config/grpc.config.ts` and repo yaml (`k8s/base/configmap.yaml`, `azure-lis-emr-v2-configmap.template.yaml`).
- v2 clients have no fallback; v1 "on-prem fallback" 192.168.60.6:30276 is dead (nc CLOSED, as recorded on 08-20).
- AKS prod live copy already had 2 keys on `lis-coresamples-v2-service.coresamplesv2.svc.cluster.local` (cluster DNS —
  works on AKS only, not on-prem).

## Fix (Leo "done" = go, 19:06Z)
- Backups of all 6 ConfigMaps: scratchpad `cm-backup-20260908T1801Z/` (session-local; note the
  `last-applied-configuration` annotation still carries the old IP and, incidentally, plaintext secrets such as
  ADOBE_CLIENT_SECRET — ConfigMap hygiene issue, pre-existing).
- `kubectl patch --type merge` on each ConfigMap for exactly the keys whose value == 10.224.0.199 → `10.224.0.10`
  (systemonly pool node; all 3 ports OPEN from on-prem 60.5 via nc; every current node serves the NodePorts).
  Readback: 8/8 keys per ConfigMap, 0 remaining except the annotation.
- Restarts: on-prem prod `rollout restart` (new pod 5968864f85-2md9w 19:07Z); AKS prod by `delete pod` (my AAD
  identity can delete pods but NOT patch deployments/exec) → 5d4784d79b-ft85q 19:08Z; staging both clusters.
  Startup logs on both prod pods: `v2 ... gRPC client created: 10.224.0.10:32100`.
- Re-drive: GenerateResultHl7 via 60.6:31317 UPDATES the existing rtr row (probe 2485882: same created_at,
  now GENERATED/TRANSMITTED, processing pod = new on-prem pod). 37 PERMANENT FAILURE samples re-driven
  (redrive_perm.txt, 10s pacing); 21 still inside auto-retry left to the pipeline, to be checked afterwards.

## Access gotchas learned today
- AKS kubectl: cluster has local accounts disabled; kubeconfig needs Azure `kubelogin` (`az aks install-cli
  --kubelogin-install-location ~/bin/kubelogin`, `kubelogin convert-kubeconfig -l azurecli`; symlinked into
  /opt/homebrew/bin). `brew install kubelogin` is the wrong project (int128 OIDC). My identity: get/list, patch
  configmaps, delete pods = yes; patch deployments, pods/exec, list nodes = no. Node IPs readable via
  `kubectl get pods -A -o custom-columns=NODE:.spec.nodeName,HOSTIP:.status.hostIP`.

## Follow-ups (not done)
- Node IPs are not stable service addresses; the next node image upgrade repeats this. coresamples-v2 already has
  an internal LB (`coresamplesv2-loadbalancer` 10.224.1.113:80→8084, reachable from on-prem); lis-core-grpc and
  lis-test-connect have none. Proposal: internal LBs (or consul DNS `lis-core-grpc.service.consul`, which on-prem
  60.5 cannot resolve today) + ConfigMap/code defaults on those addresses. Needs a ticket + PR (grpc.config.ts
  defaults, k8s yaml, template).
- No alert fired for a 100% result-generation failure lasting hours: result_fail DailyJob only reports next morning.
  A Sentry alert on GENERATION_ERROR rate (or on `14 UNAVAILABLE`) is the gap.

## Outcome (19:45Z)
- Organic pipeline healthy after restart: 2/2 non-manual pushes TRANSMITTED (first 2606688 at 19:11Z), 0 new ETIMEDOUT since 19:07Z.
- Re-drive complete: 58/58 stuck samples now have a TRANSMITTED row for every integration (37 permanent + 21 whose
  auto-retries had exhausted on the dead IP). 5 transient Power2Practice SFTP handshake failures during the 10s-paced
  batches all succeeded on retry with 20-30s spacing (labftp.power2practice.net:22 was OPEN throughout — burst-sensitive).
- Manual re-drive UPDATES the existing rtr row and leaves the stale error_message text in place (rows show
  TRANSMITTED + old "PERMANENT FAILURE ... 10.224.0.199" text). Cosmetic, but any error-text-based query must
  filter on transmission_status, not on error_message alone. 2617279 (ATHENA) instead got a NEW row; its old
  TRANSMISSION_ERROR row stays as history.
- Staging pods on both clusters restarted onto the new ConfigMaps as well.

## Order-side collateral found by hl7_fail DailyJob (2026-09-09 11:01Z)

### [2026-09-09 11:05]
- The 09-08 outcome only covered result pushes (rtr). The same dead target (coresamples-v2 NodePort 32100) also
  serves order-intake customer/patient gRPC lookups, and **8 inbound orders exhausted their retries on
  `connect ETIMEDOUT 10.224.0.199:32100` before the 19:07Z fix**: hl7_file_input 7047–7054 (THM /Prod/Orders/ ×3
  → Ocenture customer 17565; MDHQ ×5 → customers 5794, 15181, 4953, 47715, 9889). All quarantined as
  `quarantined_orders` id 3–10, status OPEN, failure_class `retry_exhausted`, expiring 09-14/09-15 → EXPIRED, no
  auto-replay. Provider resolution had succeeded (matched_integration_id set); failure was downstream gRPC.
- Pipeline healthy after fix: 7055–7058 (received ≥ 20:31Z) all parse_finished=1 with sample_id; no dead-IP errors
  after 18:18Z.
- Proposed re-place (NOT executed, awaiting Leo): `UPDATE hl7_file_input SET retry_num = 3 WHERE id IN
  (7047..7054) AND parse_finished = 0 AND retry_num = 0 AND last_error LIKE '%10.224.0.199%'`; all 7 folders are
  `pipeline_location=onprem` so the on-prem pod retries. Pre-checks: on-prem pod local file still present after the
  19:07Z rollout restart (else replay from `quarantined_orders.raw_hl7_message`), and no manual/vendor re-order for
  the same patient+DOB in lis_core_v7.sample. Then mark quarantine 3–10 RESOLVED.
- Lesson for follow-ups: after any shared-gRPC-target incident, sweep BOTH result pushes and `hl7_file_input`
  (`last_error LIKE '%<dead ip>%'`), and `retry_exhausted` quarantines need a post-fix replay path instead of
  waiting 7 days to expire. Full detail: DailyJob/hl7_fail/triage_2026-09-09.md.

## Outcome — order-side collateral closed via VP-18185
### [2026-09-11]
- The 8 retry_exhausted orders (hl7 7047-7054) were replayed 09-10 00:47-01:02Z (retry_num=3 topped up, on-prem pod), 8/8 have sample_id; quarantines 3-10 RESOLVED. Ticket VP-18185 Done.
- Still open (no ticket): stable service addresses (internal LB / DNS) + code defaults still 10.224.0.199 in grpc.config.ts / k8s yaml; Sentry alert on GENERATION_ERROR rate. Status set to resolved by dream.
