---
date: 2026-10-25
ticket: VP-18465
type: journal
tags: [vp-18465, cloud-local-proxy, retirement, zero-window, on-prem, aks]
distilled: true
---

# VP-18465 pre-flight: both zero windows verified, nothing touched

## What I explored
- Jira (Yekai's 10-20 comment supersedes the description: start 11-09, due 11-13), VP-18464 STM for the deploy and capture mechanics, the live AKS `cloud-local` namespace, Datadog, the on-prem `lis` namespace and the appserver04 capture dir, org code search, Confluence, a fresh clone of Vibrant-knowledge and platform-infra.
- Datadog had 0 `cloud_proxy_request` lines in 15 days, including 0 probe lines. Applied the "quiet window is not evidence" mirror clause: sent one probe per public front and watched it land (AKS in Datadog, on-prem in the capture log and the pod logs) before accepting the zero.

## What I ruled out
- Scaling to zero now: the on-prem window ends 11-05 and Leo set 11-09.
- A launchd job to snapshot Datadog daily: 15-day retention exactly bridges today's check to the 11-09 check.
- Editing Vibrant-knowledge: 0 references to the proxy.

## Decisions and Leo's words
- "VPN 開了，補查 on-prem" -> on-prem read; "2. 先留" -> keep the `cloud-local` namespace; "3. ok" then "請你用我的名義貼" -> comment 197567 posted as Leo.

## Outcome
- STM + `runbooks/vp18465-cloud-local-proxy-retirement.md` (Phase 1 11-09 scale, Phase 2 11-16 delete, Phase 3 archive + docs, rollback per phase). Jira comment 197567. No cluster change.

## Friction worth remembering
- `timeout` is not on macOS; use `nc -z -w 3` for reachability.
- The on-prem shared ingress has only 3 paths (vw-page + 2 proxy paths); patch by index after re-reading on the day.
- A stray Chinese phrase slipped into the English runbook and the language hook did not catch it; grep before commit.
