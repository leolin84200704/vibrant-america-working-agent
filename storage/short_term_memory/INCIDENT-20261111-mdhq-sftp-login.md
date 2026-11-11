---
id: INCIDENT-20261111-mdhq-sftp-login
type: stm
category: emr_integration
status: waiting_vendor
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
