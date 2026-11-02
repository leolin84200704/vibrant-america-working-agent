---
date: 2026-09-30
ticket: LIS-7882
slug: emr-v2-results-grpc-oauth2
tags: [lis-7882, vp-18411, emr-v2, results-grpc, oauth2, grpc-metadata]
distilled: true
distilled_on: 2026-09-30
---
# 2026-09-30 LIS-7882: emr-v2 sends OAuth2 token + x-request-id to results-grpc

**Explored**: Confluence audit doc (Yuteng), VP-18411 / VP-18528 / VP-16556 chain, results-grpc main auth interceptor (`selectJwtKey` HS256|RS256; token-less pass, bad token block), results-web PR #142 caller convention (`vibrant-oauth2-client`, strict + GRPC_OAUTH_FAIL_OPEN), transformer `createMetadatav3`, emr-v2 `shortcut.service` existing OAUTH2_* minting, both local ConfigMaps.
**Ruled out**: npm `vibrant-oauth2-client` (needs VIBRANT_CLIENT_* keys in two clusters, process.env only); strict fail-closed (server does not require token; results delivery path); ShortcutService refactor (scope creep, Leo wants minimal); cache-drop-on-auth-reject (redundant with 5-min safety + per-attempt minting).
**Decided**: OAuth2TokenService on existing config, @Optional() injection, one metadata builder for both call sites, fail-open with counted WARN + damped Sentry, x-request-id included because the audit doc lists it.
**Verified live**: probes none/real/garbage on cloud (pass/pass/block) and on-prem (older image, no interceptor; real samples return Internal server error regardless); real code path smoke sent all three keys and got 467 tests.
**Leo's words**: "A, 只要能解決doc的問題。然後改動盡量小就可以" / "commit push 開 PR".
**Result**: commit 05703c7, PR #441 -> staging.
