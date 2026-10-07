---
date: 2026-10-07
ticket: VP-18347
type: journal
tags: [vp-18347, trans-optimization, cloud-local-proxy, skin-care, dead-code, worktree-hooks]
---

# VP-18347 resume: the "last two callers" were one dormant flow and one dead method

## What I explored
- Re-synced Jira (no change since 09-30), prod trans v2 pods (CRM key still set, image moved on), Datadog (0 shipSkinCare since cutover, 0 spans anywhere on skin routes, cloud-local-proxy logs only restarts), prod DB `skin_care_ship_history` (last row 2026-08-05, 174/mo -> 0).
- LIS-backend-billing at origin/cloudproduction: traced `sendSkinCareKit` upward instead of grepping the URL. The only call is commented out (07e03c9da, 2025-08-04). The URL literal everyone cited is unreachable.
- trans v1 still serves `/utility/shipSkinCare` (my 09-30 note said otherwise) and posts to the CRM directly; its `/proxy/grpc/sendSkinPlacePatientOrders` had no caller left once prod v2 went CRM-direct.
- ConfigMap sweep across all namespaces for `skin_placepatientorders`: setting-consumer CMs already clean; key remains only where it is the proxy's own target or trans v1's live target.

## What I ruled out
- Waiting for "the next real order" as the verification: two months of zero orders and a declining trend; Leo's instruction to delete all unused trans paths made closure mode (ii) implicit.
- Redirecting billing to the CRM: wrong fix for dead code; replaced by a deletion patch.
- Deleting `lis-trans-config.skin_placepatientorders`: live for trans v1 shipSkinCare.

## Decisions and Leo's words
- Leo: 「D 刪掉，B 放在 comment 裡面 @Fangyuan Yang，然後把 Caller 2 相關的(只要是 trans/trans-v2) 並且沒有用的都刪掉」.
- Scope boundary I chose: proxy plumbing only; product routes (`/utility/shipSkinCare` on v1 and v2) untouched.
- Jira comment posted via the vibrant MCP service account because the claude.ai Atlassian write path returned 403 "app not installed" today (reads had worked earlier in the session).

## Outcome
- 6 PRs (dual-track). Staging merged + deployed + verified for all three repos (v2: env+bundle on pod image 5cf1ceb; v1: route 404 on image 7f32f92; setting-consumer: rolled). `lis-transv2-config-st` legacy key deleted. Main PRs wait for Leo; prod key deletion after #685 deploys.
- Factory lesson PR: "a reference in source is not a caller".

## Friction worth remembering
- macOS `git grep` ignores BRE `\|` silently; use `-E`.
- Factory pre-push hook in a fresh worktree: link node_modules, copy .env, link gitignored generated clients (setting-consumer `prisma2/client`); the di-smoke machine env for setting-consumer needed Azure redis keys (drift since 09-29 on main itself).
- GitHub returned "Internal Server Error" for one branch push for ~10 min; a later identical push succeeded.
- Verify a deploy by image SHA on the Deployment, not by "rollout status" alone - a neighbour's push can roll first.
