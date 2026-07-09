# VP-17312 Order-Side Cutover Runbook

> Prepared 2026-07-09 (Leo request: prep DB + code like results, NO flips yet).
> Status: **READY TO FLIP — nothing flipped.** All 198 folders `pipeline_location='onprem'`.

## 1. What already exists (shipped in VP-17312, deployed since PR #239)

| Piece | Where | State |
|---|---|---|
| DB flag | `sftp_folder_mapping.pipeline_location` ENUM('onprem','cloud') NOT NULL DEFAULT 'onprem' | 198 rows, all onprem |
| Fetch cron partition | `hl7-order-fetch.service.ts:180` — `where: { use_v2_pipeline: true, pipeline_location: PIPELINE_LOCATION }` | live on both pods |
| Retry-rescan partition | `requeueRetriableOrders()` — cloud takes `sftpDir IN (cloud folders)`, on-prem takes everything else incl. NULL/legacy | live |
| Ingest dedupe | `alreadyIngested(remotePath)` vs shared Azure DB → no double-ingest across pods | live |
| Processing affinity | fetched file → this pod's BullMQ (per-pod Redis sidecar) → same pod parses | inherent |
| Local storage | `HL7_LOCAL_ROOT=/EMR_storage/HL7Message_prod` — on-prem hostPath vs cloud Azure Files (split archive, same as results) | verified VP-17312 |
| Staging drill | Stage A A1 (flip → cloud fetches) + A2 (rollback → onprem fetches) both PASS 2026-07-07 | done |

**No code or DDL changes are needed.** Preparation gap was: reachability proof, this runbook, flip/rollback SQL.

## 2. Inbound host readiness (smoke from the CLOUD pod, 2026-07-09 ~23:30 UTC)

Folder→host resolution is `sftp_folder_mapping.emrName → emr_sftp_source` (NOT sftp_source_id).

| Host | Vendors | Folders | Cloud TCP | Notes |
|---|---|---|---|---|
| 34.199.194.51:2210 | MDHQ | **174** | **OK + SFTP login/list OK** (205 entries) | the bulk of order intake |
| 45.24.217.155:22 | 16 internal vendors (THM/ECW/OPTIMANTRA/…/ZymeBalanz) | 16 | OK | Vibrant's own SFTP |
| 45.24.217.150:2222 | PF | 1 | OK | Vibrant's own SFTP |
| external.sftp.athena.io | ATHENA | 1 | OK | |
| labs.elationemr.com | ElationEMR | 1 | OK | |
| ftp4labs.insynchcs.com | INSYNC | 1 | OK | |
| sftp.healthfusionclaims.com | HF | 1 | OK | |
| 64.124.9.100:2222 | Breathermae | 1 | **TIMEOUT** | likely IP-allowlist; folder also DORMANT (0 inbound files in 30d) — keep onprem until allowlist or retirement confirmed |

Orphans (skipped by fetch on BOTH sides today — no emr_sftp_source row; pre-existing, not a cutover issue): folder 74 `Rupa Health /test/orders/`, folder 251 `FOLLOWTHATPATIENT /Prod/FollowThatPatient/Order/`.

## 3. Flip rules (orders)

1. **Unit = folder.** Folders are disjoint fetch sets; no whole-destination/whole-customer coupling (that is a results-side rule).
2. **Drain before flip** (the one hard rule): a folder's retriable rows re-read the fetched .hl7 from POD-LOCAL storage, which does not move with the flag. Before flipping folder F:
   ```sql
   SELECT id, file_name, retry_num FROM hl7_file_input
   WHERE parse_finished=0 AND retry_num>0 AND sftpDir='<server_folder>';
   ```
   Must be 0 rows (wait for retries to exhaust/succeed, or resolve them) — same in reverse for rollback (cloud-fetched retriable files live on the cloud PVC).
3. Flip in the :00-:15 gap between fetch ticks (cron on :00/:15/:30/:45); the flag is read fresh each tick, no restart needed.
4. Orders-loss asymmetry: a missed result is re-derivable (repush); a lost order is not. Hence results-first overall, and per-folder canary before waves.

## 4. Recommended sequence (each step gated on Leo)

1. **Canary**: INSERT a ZymeBalanz test folder row (`/Test/Order/` on .155, use_v2_pipeline=1, pipeline_location='cloud' — prod has no ZymeBalanz order folder today; mirrors Stage A's staging folder 73). Leo/agent drops a test order file → cloud pod fetches/parses it. Zero real-order risk. DELETE the row after.
2. **Wave 1**: 45.24.217.155/.150 internal folders (17) — Vibrant-owned hosts, lowest external risk.
3. **Wave 2+**: MDHQ's 174 folders in chunks (e.g. 20 → 50 → rest), watching fetch-tick logs + `hl7_file_input.last_update_pod_name`. MDHQ per-IP connection-limit history (VP-17217) argues for chunking.
4. Single-folder externals (Athena/Elation/INSYNC/HF/PF) anytime after wave 1.
5. **Breathermae: DO NOT FLIP** until 64.124.9.100 allowlists AKS egress 20.14.29.219 — or confirm the integration is dead (0 files in 30d) and retire it.

## 5. SQL templates (app account lis_emr for writes)

```sql
-- snapshot (run + save before any flip)
SELECT id, emrName, server_folder, pipeline_location FROM sftp_folder_mapping
WHERE use_v2_pipeline=1 ORDER BY id;

-- flip a bounded folder list to cloud
UPDATE sftp_folder_mapping SET pipeline_location='cloud'
WHERE id IN (<ids>) AND pipeline_location='onprem';

-- rollback
UPDATE sftp_folder_mapping SET pipeline_location='onprem'
WHERE id IN (<ids>) AND pipeline_location='cloud';

-- post-flip verification: new rows must carry the CLOUD pod name for flipped folders
SELECT sftpDir, last_update_pod_name, COUNT(*), MAX(received_time)
FROM hl7_file_input
WHERE received_time >= '<flip time>' GROUP BY 1,2;

-- intake regression guard (any folder)
SELECT COUNT(*) FROM hl7_file_input
WHERE parse_finished=0 AND retry_num=0 AND received_time >= NOW() - INTERVAL 1 HOUR;
```

## 6. Monitoring plan at first order flip

Extend the 30-min watch with: per-flipped-folder `hl7_file_input` rows must carry the cloud pod name; fetch-tick log line `Scanning N v2-enabled SFTP folder(s) [cloud]` shows N>0 on the cloud pod; parse failures (`parse_finished=0 AND retry_num=0`) attributable to flipped folders = anomaly; on-prem pod must show no fetch activity for flipped folders.
