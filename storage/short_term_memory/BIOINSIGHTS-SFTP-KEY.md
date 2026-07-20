---
id: BIOINSIGHTS-SFTP-KEY
summary: BioInsights SFTP account is key-only (no password) — added sftp_private_key columns to all 3 credential stores + plumbed privateKey through result-push and order-fetch pipelines. PR #275 (draft, target staging). Migration APPLIED to staging+prod 2026-07-20, live-verified.
status: active
category: emr_integration
created: 2026-07-20
updated: 2026-07-20
---

# BIOINSIGHTS-SFTP-KEY — key-based SFTP auth support

## Context

- BioInsights provisioned `vibrant-wellness @ sftp.bioinsights.com:2022`, **key-based auth only** (no password on either end). Customer verified the account works via WinSCP with their key.
- All 3 credential stores (`ehr_vendors.sftp_password`, `ehr_integrations.sftp_password`, `emr_sftp_source.password`) were password-only → neither pipeline could auth.
- `SftpConnectionService` already supported `privateKey` (PEM, preferred over password) — only the admin manual-connect API used it; DB-driven paths did not.
- No Jira ticket exists for BioInsights (JQL `text ~ "BioInsights"` = 0 hits, 2026-07-20).

## Work log

### [2026-07-20]

Leo approved: key stored plaintext in DB (same posture as existing passwords; encryption = follow-up covering both), both pipelines, 3 commits for stepwise rollback.

- Branch `feature/leo/bioinsights-sftp-key` off origin/staging, PR **#275 draft → staging**: https://github.com/Vibrant-America/lis-backend-emr-v2/pull/275
- Commit 1 `b6dc99d` schema only: nullable `sftp_private_key TEXT` (ehr_vendors, ehr_integrations), `private_key TEXT` (emr_sftp_source) + `prisma/migrations/20260720_add_sftp_private_key/migration.sql` + schema.test.prisma sync
- Commit 2 `517e396` result push: `getSftpConfig()` resolves key (vendor or integration level), `uploadHL7File` → `connect({privateKey})`
- Commit 3 `365e30b` order fetch: `loadCredentialStores()` accepts password-OR-key rows (was password-only → key-only folders silently skipped at `hl7-order-fetch.service.ts` guard), key carried through `HostGroup`; VP-17385 drift diff now includes `privateKey` (field names only, never values)
- Tests: sftp.service.spec 7 passed (4 new), hl7-order-fetch.service.spec 30 passed (5 new), full suite 83/83 suites / 890 passed, nest build clean
- Worktree removed after push (feedback_delete_worktree_after_ticket)

## Deploy order (critical)

Prod is NOT Prisma-managed. Apply migration SQL to staging (192.168.60.11) + prod (lisportalprod2) **BEFORE** deploying code — commits 2/3 `select` the new columns; deploy-first = 500 on those queries (VP-16832 class).

### [2026-07-20 15:40] Migration APPLIED to both DBs (Leo directed)

- Runner: `scripts/_bioinsights-sftp-key-migrate.ts` (mysql2, idempotent pre-check + row-count guard + 100% column verify + dormant check); probe: `scripts/_bioinsights-live-probe.ts` (both gitignored `_*.ts`)
- **Staging** 192.168.60.11: 3 columns added, TEXT/nullable OK, rows 11/46/3 unchanged, all NULL
- **Prod** lisportalprod2: 3 columns added, TEXT/nullable OK, rows 33/1268/30 unchanged, all NULL
- Unit suite re-run on PR branch in fresh worktree: 83/83 suites, 890 passed
- **Live verify (prod, post-ALTER)**: old-code column-set reads on all 3 tables OK; order-fetch cron 15:45 tick ingested a new hl7_file_input row (received_time 15:45:23 > migration ~15:41) = order pipeline healthy on migrated DB. Result push: no organic traffic since (event-driven, Sunday), but its reads verified via the column-set probe.
- DB now AHEAD of deployed code (safe direction). PR #275 can merge anytime.
- Gotcha: `hl7_file_input` has NO created_at — use `received_time` / `updated_time`

## Open items

- [ ] Leo review/merge PR #275 (DB precondition DONE both envs)
- [ ] Vendor row setup for BioInsights (ehr_vendors INSERT incl. the PEM key — receive key via secure channel, NOT Jira/Slack)
- [ ] Possibly file a Jira ticket for the BioInsights integration and link PR
- [ ] Encryption follow-up: encrypt sftp_password + sftp_private_key at rest (schema comment has flagged this since before)
