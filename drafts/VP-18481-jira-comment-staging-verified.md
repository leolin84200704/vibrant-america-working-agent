# Draft Jira comment for VP-18481 (not posted)

Staging verification done (2026-10-13).

- trans stage_test (PR #920, image 0d4533d) now runs the LIS-Sample data plane: 4 Prisma clients, `storage-info-updates` queue consumer, `storage_event_outbox` drainer + topic producer, behind `SAMPLE_CONSUMERS_ENABLED` / `STORAGE_DATA_UPDATES_EMIT_ENABLED` (both `true` on `lis-trans-config-st`; legacy import cron stays off).
- Staging Service Bus entities created by Tianhao in `general-system-events`: queue `storage-info-updates-staging`, topic `storage-data-updates-staging` (duplicate detection 24 h), subscription `lis-test-web-generation-subscription`. Settings verified against the prod entities.
- Staging `lis_inventory` (192.168.60.11) now has `storage_event_outbox` (DDL from LIS-Sample `db/migrations/storage_event_outbox.sql`).
- Replay against the real staging queue, all passed: new rack/record, exact duplicate (rejected by the unique key, one extra UPSERT_RACK as in LIS-Sample), archiveTime older than 7 days (completed without DB write), message published while the pod was down (consumed by the replacement pod), message locked by a consumer that died (redelivered at lock expiry and consumed). Outbox 7/7 sent, queue active/dead-letter 0, subscription received `messageId = outbox-{id}` for every row.
- Now soaking for a week on staging. Remaining: `enableShutdownHooks()` PR for trans (separate), main-twin PR after the soak, prod cutover per the runbook in the design note.
