---
id: INCIDENT-20261111-mdhq-sftp-login
type: stm
category: emr_integration
status: in_progress
created: 2026-11-11
updated: 2026-11-11
links: [INCIDENT-20260529]
tags: mdhq cerbo sftp unexpected-end-event result-push zendesk-785091 resilience-code
---

## Context
Zendesk #785091 (Zhenhe Zhang, Vibrant support -> Cerbo support, Leo CC'd, Resilience Code CC'd), 2026-11-11 21:41Z:
MDHQ result uploads fail with "SFTP connection failed after 3 attempts: getConnection: Unexpected end event".

## Findings
### [2026-11-11 22:00]
- Prod pod lis-emr-v2-deployment-prod-8fc6dbd8f-kfsvc (egress 20.14.29.219). Log 06:30-21:45Z: MDHQ 34.199.194.51:2210
  OK at 07:00 and 07:10Z, then 14 x attempt-3/3 failures 16:03-19:32Z (~640 ms each). BioInsights/Nextech 62 OK each.
- From the pod: handshake with a bogus username -> normal "All configured authentication methods failed";
  with the real vibrantamerica credential -> handshake ok, server closes at 638 ms, no auth reply.
  Same pattern as INCIDENT-20260529 -> account-level block on Cerbo side (locked/disabled/password/IP rule). No code issue.
- result_transmission_records TRANSMISSION_ERROR for MDHQ today: client 11078 /bliemr (16:02Z), 18832 /drleveroneemr (17:24Z),
  4953 /rcode (19:04Z). Need retry after Cerbo fixes the account.
- MDHQ order fetch is not on this pod (fetch cron scans 2 folders only), so orders were not checked here.

## Progress
### [2026-11-11 22:00]
- Reply-all draft saved in Leo's Outlook (asks Cerbo to check the vibrantamerica account, gives IP and time window). Waiting Leo ok.

### [2026-11-11 22:30] Cerbo answer + correction
- Scott (Cerbo, 22:11Z): resolved; our connections stayed open and the account hit its 20 concurrent-session limit. Asked us to close sessions after each upload.
- My earlier read (account locked) was wrong: the immediate close after login was the session cap. First draft (id ...XsXgAA) is obsolete, Leo should discard it.
- Pod login with vibrantamerica now READY (657 ms).
- AKS prod pod opened only 2 MDHQ sessions today (07:00, 07:10Z), both SFTP_CLOSE graceful -> not the leak source. Staging pod: 0 MDHQ connects.
- MDHQ order intake (hl7_file_input emr_service=MDHQ): 2 at 02:xx, then nothing until 22:15:51Z (right after Cerbo cleared sessions).
  Normal is 7-10/day. MDHQ order fetch runs on the on-prem intake pod (no kubectl context here). Suspect: on-prem fetch leaks sessions
  (same family as INCIDENT-20260604). Not verified; needs on-prem logs.
- Failed results to resend: sample 2649139 (client 11078), 2661089 (18832), 2618604 (4953 rcode); none retransmitted yet.
- New reply-all draft on Scott's mail (id ...XwYQAA). Waiting Leo ok.

### [2026-11-11 22:25] Repush done (Leo: "回覆並且把缺的報告重新傳")
- Pre-check: all 3 integrations LIVE, result_enabled=1, pipeline_location=cloud, vendor 1.
- In-pod gRPC localhost:5000 GenerateResultHl7 {send_result:true}, 8 s pacing, Bearer token from pod OAUTH2_* client_credentials
  (metadata authorization + service-name=manual-repush-mdhq-20261111; without token -> 16 UNAUTHENTICATED missing_token).
- All 3 success; same rtr rows flipped to TRANSMITTED 22:23:19 / 22:23:41 / 22:24:54Z.
- SFTP stat on Cerbo: /bliemr/results/2610076569.hl7 600101 B, /drleveroneemr/results/2610286378.hl7 189366 B,
  /rcode/results/2608186799.hl7 4426280 B; all equal to file_size_bytes. 3/3 verified.
- Draft reply to Scott updated to "we have resent". Body replace dropped the quoted thread. Waiting Leo "ok".
- Open: on-prem intake pod session leak (unverified, no on-prem access).
