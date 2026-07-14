# VP-17312 Watch v8 — 30-min prod monitoring prompt

> Canonical copy of the session-cron prompt (cron `13,43 * * * *`, session-only,
> 7-day expiry — re-create with CronCreate from THIS file after a session restart).
> v8 adds ghost LIVE CAPTURE to Step 6. Changes to this file = automation
> behavior change → PR.

## Changelog
- v8 (2026-07-14): Step 6 ghost detector gains LIVE CAPTURE: on new_tmp>0,
  same-tick PROCESSLIST snapshot (app account, full HOST incl. port),
  classify sources (10.224.x = AKS legit; 45.24.217.146 = office NAT shared
  by legit on-prem pod AND any office machine — excess connection group =
  ghost pool), record received_time (UTC) as the correlation key for IT
  firewall/NAT lookup. Clean baseline 2026-07-14: AKS 9 conns, NAT 11 conns.
  Also: repush is_cloud=0 rows documented as expected; row 6590 rescued
  (sample 2595956, duplicate watch if vendor re-sends).
- v7 (2026-07-14): +Step 5 failure diagnosis: snapshot pod-log evidence to
  storage/failure-evidence/ at detection time, LLM-diagnose root cause, UPDATE
  hl7_file_input.error_detail (bounded single-id, app account). Per Leo:
  diagnosis lives in the agent layer, not emr-v2 code (PR #266 reduced to
  schema-only). Known-broken vendors excluded from re-alerting.
- v6 (2026-07-11): batch-4 scale; cloud vendor aggregate + dynamic rs hash.

## Prompt (paste verbatim into CronCreate)

[VP-17312 batch1-4 watch v7] 505 integrations on cloud (MDHQ ×403 dominant + THM/OPTIMANTRA/ECW etc.). Run checks quietly; report to Leo in zh-TW ONE line if all OK, details on anomaly.
1. Pod health: AKS `kubectl exec -n emr-v2 deploy/lis-emr-v2-deployment-prod -c lis-emr-v2-prod -- wget -qO- http://localhost:3000/api/v1/health` (retry once on kubectl flake). On-prem `curl -s -m 8 http://192.168.60.6:31318/api/v1/health` — if VPN down note briefly, use indirect evidence; NEVER `vpn connect`.
2. Prod DB (mysql client + creds: long-term-memory/access-and-secrets.md §2a):
   a. records last 35 min: COUNT + SUM gen/tx errors — errors>0 = anomaly (sample_ids + emr_service).
   b. stuck whole-order PENDING (push_scope_key IS NULL, 30min-24h old) — >0 = anomaly.
   c. partial leak: push_scope_key IS NOT NULL only on 'cvp17344e2etest%' integrations.
   d. intake: hl7_file_input parse_finished=0 AND retry_num=0 last 35 min — mention if >0.
3. CLOUD VENDOR AGGREGATE: SELECT emr_service, processing_pod_name LIKE '%<current-cloud-rs-hash>%' is_cloud, COUNT(*), SUM(transmission_status='TRANSMITTED') FROM result_transmission_records WHERE emr_service IN ('MDHQ','OPTIMANTRA','THM','ECW','VEJO','VEJOEcomm','VejoProgram','Unprescribed','YHL','GLO','HealthMatters','PRAXISEMR') AND created_at >= NOW() - INTERVAL 40 MINUTE GROUP BY 1,2; (resolve rs hash via kubectl get pods first). ANOMALIES: is_cloud=0 EXCEPT the 3 exclusions (cust 15185 MDHQ /theloganinstitute/, cust 5784 OPTIMANTRA, clinic 7145 OPTIMANTRA); any sent<count → investigate. If MDHQ stuck also grep cloud pod logs for sftp errors (VP-17217 history).
4. 999997 test-batch detection (not daily; last 2026-07-08): new rows result_client_id=999997 last 35 min → verify VP-17344 full matrix (whole-order …/Kafka + …/VP17344 + …/VP17344R; SAMPLE_TYPE:* on cvp17344e2etest0000000001; REPORT:* on …0002; all TRANSMITTED) → full organic E2E report.
5. FAILURE DIAGNOSIS (VP-17412, agent-layer design per Leo 2026-07-14): find newly-failed order rows: SELECT id, file_name, sftpDir, emr_service, emr_code_not_found, customer_not_found, retry_num, parse_finished, localDir, last_update_pod_name, error_detail FROM hl7_file_input WHERE (emr_code_not_found IS NOT NULL OR customer_not_found IS NOT NULL OR (parse_finished=0 AND retry_num < 5)) AND error_detail IS NULL AND last_parse_time >= NOW() - INTERVAL 40 MINUTE; plus result-side TRANSMISSION_ERROR/GENERATION_ERROR rows last 40 min. For EACH hit:
   a. IMMEDIATELY snapshot evidence BEFORE it is lost to a redeploy: kubectl logs (cloud pod, --since=50m, grep around the id/file_name); on-prem logs unreachable — note when the failing row is on-prem. Save raw evidence + row dump to storage/failure-evidence/<YYYY-MM-DD>-hl7-<id>.md and git commit to main (evidence files are data, direct commit OK per Leo).
   b. Diagnose the root cause (LLM): emr_code_not_found → reverse-lookup code ownership (VACP: bundle owner vs NPI resolution winner — ehr_integrations for the NPI's customers, rank LIVE+ordering by FULL_INTEGRATION>ORDER_ONLY then updated_at DESC; VATEST/VAREQU → orderability; VASC → Get Shortcuts API catalog); customer_not_found → near-misses (rows exist but not LIVE/ordering_enabled); file-missing//tmp → ghost-process storage explanation; sendOrder/payment → upstream error from logs.
   c. Write the full English explanation to DB: UPDATE hl7_file_input SET error_detail='<explanation>' WHERE id=<id>; using the app write account (access-and-secrets.md, user lis_emr). Bound every UPDATE to the explicit id.
   d. Report the diagnosis to Leo in the tick summary (1-2 lines per failure).
6. GHOST DETECTOR + LIVE CAPTURE: SELECT COUNT(*) new_tmp FROM hl7_file_input WHERE localDir LIKE '/tmp/%' AND received_time >= NOW() - INTERVAL 40 MINUTE; — if >0, in the SAME tick immediately (ghost's Prisma pool may still be connected):
   a. SELECT HOST, USER, COMMAND, TIME, STATE, INFO FROM information_schema.PROCESSLIST WHERE USER IN ('lis_emr','lis_core_emr') ORDER BY HOST; via the app account — full HOST incl. source port.
   b. Classify source IPs: 10.224.x.x = AKS cloud pod (legit); 45.24.217.146 = office NAT (SHARED by legit on-prem pod AND any office machine). Compare per-IP connection count against clean baseline (2026-07-14: AKS 9, NAT 11) — excess group on the NAT = ghost pool; record its ports.
   c. Snapshot ghost row dump + processlist + exact received_time (UTC) to storage/failure-evidence/<date>-ghost-<id>.md, commit. received_time is the correlation key for IT firewall/NAT lookup (outbound to the vendor SFTP host at that instant).
   d. Report processlist findings to Leo.
Context: batch-4 flipped 2026-07-10 (MDHQ 403 etc.; snapshots scratchpad vp17312_batch{1..4}_snapshot.tsv; rollback = UPDATE ids back to onprem). Cloud/onprem = 505/530. Remaining onprem: cust 15185 (P2P), cust 5784 (ChARM), clinic 7145 (P2P), batch-5 externals blocked on egress 20.14.29.219 allowlist. VP-17344 partial dormant (2 test integrations). Row 6590 rescue awaiting Leo approval. Known-broken vendors (do not re-alert): Cascades (host dead since 6/18, 2 samples stranded, PM outreach), Marqimedical (DNS dead, dormant).
