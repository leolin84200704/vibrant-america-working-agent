---
id: SFTP-ARCHIVE-ON-FETCH
title: HL7 order fetch — archive remote SFTP files instead of deleting (accidental-deletion guard)
status: in_review
category: emr_integration
created: 2026-07-21
updated: 2026-07-21
---

# SFTP-ARCHIVE-ON-FETCH — archive instead of delete on order ingest

## Ask (Leo, 2026-07-21)
因應誤刪檔案問題：EMR workflow 的 SFTP 下載後不再刪除 vendor 端檔案，改移到 `server_folder/archive`。Leo 問是否要為每個 `sftp_folder_mapping.server_folder` 手動/schema 加 archive folder — 答案：不用，runtime 推導 + lazy mkdir。

## Outcome
- PR #279 (draft) → `staging`: https://github.com/Vibrant-America/lis-backend-emr-v2/pull/279
- Branch `feature/leo/sftp-archive-on-fetch` (from origin/staging b83efc2), no Jira ticket at time of work.

## Key decisions / findings
### [2026-07-21 10:50]
- **`SftpFileService.moveFile` was a fake stub** (`sftp-file.service.ts:507` pre-change): logged
  "File moved successfully" without ever calling the client. Anyone calling it got silent
  success. Now real `client.rename()` + `SFTP_MOVE_OP_TIMEOUT_MS` (15s default).
- **No DB change needed**: archive dir = `path.posix.join(server_folder, 'archive')` derived at
  runtime; `createDirectory` (idempotent, existed already) called lazily once per folder per
  tick. `listFiles` filters `isFile` → archive subdir never re-ingested; `alreadyIngested()`
  keys on original remote path → unaffected.
- **Failure semantics = degrade like old delete-failure**: WARN + file stays in pickup folder
  (re-listed every tick, never re-processed). Deliberately NO fallback-to-delete — the whole
  point is recoverability. Vendor accounts that deny mkdir/rename land here; flip back per
  cluster via `HL7_REMOTE_POST_FETCH_ACTION=delete` (env-only rollback switch, default archive).
- Name collision on re-sent filename: one retry with timestamp-suffixed name.
- Config coupling (Gate 4 / pre-commit hook): `SFTP_MOVE_OP_TIMEOUT_MS` +
  `HL7_REMOTE_POST_FETCH_ACTION` added to untracked live pair `lis-emr-v2-config.yaml`/`-prod`
  (main checkout), configmap template, and all 4 deployment yamls. NOTE: the hook checks the
  worktree root for the untracked pair — fresh worktrees need the two files copied in or the
  commit is blocked.
- Fresh-worktree test env: needs `npm ci` + `npx prisma generate` (main schema) + `npx prisma
  generate --schema prisma/schema.test.prisma` (test client), else 5 suites fail with
  "Cannot find module .prisma/test-client". Symlinking main checkout's node_modules is wrong
  when schemas diverge across branches (stale prisma client type errors).
- Tests: 83/83 suites, 895 passed. New coverage for archive path, collision retry,
  both-moves-fail, mkdir-denied, delete rollback switch, real moveFile unit tests.

## Open items
- Leo review/merge PR #279 (staging → later promote to main per repo flow).
- Post-deploy watch: `Could not ensure archive dir` / `Remote archive failed` WARNs = vendor
  permission gaps (esp. MDHQ multi-tenant host, Athena inbound folders).
- Vendor-side archive growth unbounded — retention policy later if quota complaints.
- Legacy Java EMR-Backend path unchanged (order fetch is fully on v2 since use_v2_pipeline
  full-table cutover; v1 delete code is dormant).
