---
date: 2026-11-04
ticket: VP-18336
type: journal
tags: [nextech, ehr-vendors, is_public, go-live, prod-data]
related: [NEXTECH-onboarding, BIOINSIGHTS-onboarding]
distilled: true
---

# Nextech go-live: vendor 47 is_public 0 -> 1

## What happened
Mail thread (MAIL-2216263296): Jessica (Nextech) asked if more testing was needed; Support replied ready to go live; Jessica thanked. Nothing to reply. The one leftover from VP-18336 step 4 was `ehr_vendors.is_public` still 0. Proposed it, Leo said "ok", applied 2026-11-04 18:43:44Z.

## Reasoning worth keeping
- is_public only drives the Website vendor list (`ehr-vendor.service.ts` default filter is_active=1 AND is_public=1); routing for an existing LIVE integration does not read it. So the flip is low-risk and independent of the practice's own go-live.
- A data-only change has no code to PR. The "approved plan" step after the fact (Steps 5-7) reduces to re-verifying prod and recording; opening an empty PR would be noise.

## Mechanics
- emr-v2 runner scripts need `node -r dotenv/config` (Prisma does not load .env by itself from plain node).
- Pattern: pre-check snapshot (SELECT *), UPDATE bound to id + code + old value, assert 1 row, compare every other column in-tx, dry-run via thrown sentinel to roll back, then APPLY=1; second read via the MCP read-only connection.
- Rollback: `UPDATE ehr_vendors SET is_public=0 WHERE id=47;`
