# VP-18481 — LIS-Sample → trans, Phase B: data and infra plane (design note + cutover runbook)

Status: DRAFT for Leo's review (2026-10-13). Goes to Confluence as a child of the roadmap page (2711453698) next to the Phase A page (2727378970) once approved.

## 1. What Phase B delivers

LIS-Sample's non-route surface, hosted inside trans v1 (`LIS-transformer`, `src/sample/`), behind switches that default to off:

| Piece | In trans as | Switch | Notes |
|---|---|---|---|
| 3 MySQL DBs (4 used Prisma clients) | `SamplePrismaModule` | none (always available) | lis_inventory master; vibrant_america_information master + slave; vibrant_tracking slave. The lis_inventory slave and vibrant_tracking master clients are never injected in LIS-Sample and are not ported. |
| Outbox table service + topic producer | `SampleEventsModule` | none (`sendOne` must serve Phase C routes) | `storage_event_outbox` in lis_inventory; topic `storage-data-updates` |
| Outbox drainer (10 s) + cleanup (03:00 LA) | `StorageEventOutboxDrainerService` | `SAMPLE_CONSUMERS_ENABLED` | DB `UPDATE ... locked_by` claim; Redlock is a courtesy |
| `storage-info-updates` queue consumer | `StorageInfoQueueConsumerService` | `SAMPLE_CONSUMERS_ENABLED` | replaces LIS-Sample's `NODE_ENV=prod` start condition; queue name from `STORAGE_INFO_UPDATES_QUEUE` |
| Daily legacy storage import (09:15 LA) | `StorageLegacyImportService` | `SAMPLE_LEGACY_IMPORT_ENABLED` | own switch; reads on-prem MySQL 192.168.60.2 |
| Redis | Redlock client built from `REDIS_URL` + `REDIS_LOCK_PREFIX` | — | same identity as LIS-Sample by construction. Cache keys NOT ported (Phase C). |
| Kafka | not ported | — | LIS-Sample has one producer (patient demographic updates) and no consumer; it moves with the patients family. |
| Ingress | unchanged | — | `/v1/lis/samples` keeps pointing at LIS-Sample until Phase C moves families. The trans rule must live in ns `default` (`k8s-ingress`), not ns `sample`. |
| Pipeline | trans GitHub Actions | — | `prisma:generate` + both Dockerfiles gained the four schemas. LIS-Sample Jenkins stays until retirement. |

Code: LIS-transformer `feature/leo/VP-18481` (d258856) / `-stage` (ad18e3f, PR #920 → stage_test).

## 2. Facts the design rests on (verified 2026-10-13)

- LIS-Sample prod: 3 replicas, no `resources`; staging 1 replica. All three prod pods run the queue consumer and the drainer concurrently today (every pod hostname appears in `storage_event_outbox.locked_by`). No on-prem LIS-Sample exists (checked on appserver04 across all namespaces); the June outbox doc's on-prem consumer is gone.
- Prod outbox: 39,405 rows, 0 unsent, 0 dead-lettered; DI-V3 machine events ≈ 260/day; manual UPSERT_RECORD ≈ 2,200/day.
- Databases: lis_inventory = Azure MySQL 8.4.9 (`max_connections` 2731, ~446 in use). vibrant_america_information and vibrant_tracking = on-prem MySQL 5.7.43 at 192.168.60.2:3307, `max_connections` 400, `Max_used_connections` 393 — master/slave are the same server under different accounts. Staging: all six URLs point at 192.168.60.11 `lis_inventory` (no outbox table; `prod_sample_storage` and `service_call_records` live in that schema).
- Service Bus `general-system-events` (Standard, SAS auth on): queue `storage-info-updates` (lock 1 min, max delivery 10, TTL 14 d, dup off; 220 dead-lettered messages from 2026-02-07 and 2026-07-19, all `MaxDeliveryCountExceeded`, nothing recent), topic `storage-data-updates` (dup detection 24 h) with subscriptions `lis-test-web-generation-subscription` and `clickhouse-writer`. No staging entities exist. Creating entities needs Contributor on the namespace (Owners: Tianhao, Alex); the agent account only has Data Owner + Reader.
- DI-V3 publishes one record per message without `messageId` and retries once on a fresh client → at-least-once. LIS-Sample's handler is idempotent on the unique keys (`sample_racks` rack_id+rack_type, `sample_storage_records` row+col+rack_serial_number).
- trans prod: 3 replicas, memory request 2Gi, no limits, `terminationGracePeriodSeconds` 30, no preStop, `enableShutdownHooks()` never called (separate PR).

## 3. Decisions

1. **Hosting = every trans replica** (Leo, 2026-10-13). Same shape as LIS-Sample today. Safety: DB claim for the drainer, peekLock + unique keys for the consumer, Redlock for the legacy cron. No leader election, no worker Deployment.
2. **Two switches, not one.** The legacy cron is the only piece whose cross-service guard is a 5 min Redlock; it stays off in trans until LIS-Sample's cron is off.
3. **Cache deferred to Phase C.** No route in trans reads `operation-settings:*` / `user:name:by:id:*` before the families move.
4. **Pool budget.** lis_inventory client keeps `connection_limit=10&pool_timeout=20` (Azure has headroom). The three on-prem clients use `connection_limit=1` (LIS-Sample uses 2 per client per module; the server sits at 393/400 max-used).
5. **Port verbatim.** The only diffs against LIS-Sample master 19fbb0f are the switch checks, the queue-name env, and closing the legacy cron's Redis client on shutdown.

## 4. Configuration

`lis-trans-config-st` (staging, before enabling anything):

| Key | Value |
|---|---|
| `SAMPLE_CONSUMERS_ENABLED` | `false` → `true` at step 5.3 |
| `SAMPLE_LEGACY_IMPORT_ENABLED` | `false` |
| `STORAGE_INFO_UPDATES_QUEUE` | `storage-info-updates-staging` |
| `STORAGE_DATA_UPDATES_TOPIC` | `storage-data-updates-staging` |
| `STORAGE_DATA_UPDATES_EMIT_ENABLED` | `false` → `true` at step 5.3 |
| `REDIS_LOCK_PREFIX` | `sample::lis_sample::staging::` |

Secret (prod and st currently share `lis-trans-secret` — decide: per-env key names, or split the secret):

| Key | Source |
|---|---|
| `DATABASE_URL_LIS_INVENTORY_MASTER` | copy from `lis-sample-secret-{prod,dev}` |
| `DATABASE_URL_VA_INFO_MASTER`, `DATABASE_URL_VA_INFO_SLAVE`, `DATABASE_URL_VIBRANT_TRACKING_SLAVE` | copy, with `connection_limit=1` for prod |
| `REDIS_URL`, `REDIS_PASSWORD` | copy (same Azure cache trans already uses) |
| `AZURE_SERVICE_BUS_CONNECTION_STRING` | copy (`Two-way` SAS for prod; staging needs Send+Listen as well) |

`lis-trans-config` (prod): the same keys with `SAMPLE_CONSUMERS_ENABLED=false`, `SAMPLE_LEGACY_IMPORT_ENABLED=false`, `STORAGE_INFO_UPDATES_QUEUE=storage-info-updates`, `STORAGE_DATA_UPDATES_TOPIC=storage-data-updates`, `STORAGE_DATA_UPDATES_EMIT_ENABLED=true`, `REDIS_LOCK_PREFIX` empty. Drift baseline: VP-18458.

## 5. Staging plan (the ticket's Done criterion)

1. Service Bus (Contributor needed): queue `storage-info-updates-staging` (lock PT1M, max delivery 10, TTL P14D, dead-letter on expiry), topic `storage-data-updates-staging` **created with duplicate detection on, 24 h window** (immutable afterwards), subscription `lis-test-web-generation-subscription` on it.
2. DDL: `db/migrations/storage_event_outbox.sql` from LIS-Sample on staging `lis_inventory` (192.168.60.11), linted with the Gate 3 checker first. Side effect, accepted: the LIS-Sample staging pod starts writing outbox rows for staff actions on staging; nothing drains them until trans-st is on. Amend `docs/storage-event-outbox.md` §"Staging DBs are intentionally NOT migrated".
3. ~~Merge PR #920, wait for `lis-transformer-deploy-staging`~~ Done 2026-10-13 (merge 0d4533d, st pod Ready, 0 restarts). Note: trans boots Nest with `['error','warn']` only (`main.ts:51`), so the ported code's `logger.log` lines (idle notices, "listener started", per-message "Successfully processed", drainer batch summaries) never appear in trans logs. All verification below reads the DB and the queue counters instead. Until the §4 keys exist the st pod logs one `[sample-prisma] ... Environment variable not found` warning per client and `[storage-event] AZURE_SERVICE_BUS_CONNECTION_STRING is not set` — expected.
4. Add the keys from §4, flip `SAMPLE_CONSUMERS_ENABLED=true` and `STORAGE_DATA_UPDATES_EMIT_ENABLED=true` on `-st`, rollout restart.
5. Replay script (`@azure/service-bus`, Send SAS): publish three `ArchiveRecordMessage` shapes without `messageId` — a new rack, the same record a second time, a record with `archiveTime` 8 days old — then kill the trans-st pod while a fourth message is in flight. Assert: `sample_racks` / `sample_storage_records` rows; the duplicate produced a second `UPSERT_RACK` outbox row and no second `UPSERT_RECORD`; the old record was completed without DB writes; outbox rows carry `locked_by = <trans-st pod>-<pid>` and `sent_at`; the subscription received messages with `messageId = outbox-{id}`; queue active 0, dead-letter 0; the in-flight message was redelivered and completed after the restart.
6. Leave it running for a week with the LIS-Sample staging pod's own outbox traffic flowing through trans-st.

## 6. Production cutover runbook (consumers)

Pre-conditions: §5 done; keys in `lis-trans-config` + secret; `enableShutdownHooks()` PR merged; someone watching Datadog.

| Step | Action | Verify (input side first) |
|---|---|---|
| 0 | Record baselines: queue active/dead-letter counts, `storage_event_outbox` unsent count, DI-V3 publish count for the last hour (its "Published archive record" log) | numbers written in the ticket |
| 1 | `SAMPLE_CONSUMERS_ENABLED=true` on `lis-trans-config`, rollout restart `lis-trans-deployment` | no new `error`/`warn` lines from `StorageInfoQueueConsumerService` / `StorageEventOutboxDrainerService` on the trans pods (their info lines are not emitted in trans); within 10 min `storage_event_outbox.locked_by` shows `lis-trans-deployment-*` hostnames; both services now consume (competing consumers, no gap possible) |
| 2 | Watch one hour | DI-V3 publishes in the hour = new `sample_storage_records` rows with `archived_by` = instrument users in that hour (LIS-Sample's own "Successfully processed" lines account for its share); queue active 0 and dead-letter unchanged; outbox unsent stays 0; results-web subscription active 0 |
| 3 | Stop LIS-Sample's consumer | needs a LIS-Sample change (its consumer starts unconditionally under `NODE_ENV=prod`): a flag PR for Zhibin/Michael to merge, or wait for the Phase C scale-down. Until then both services keep consuming; that is safe (idempotent upserts, duplicate detection on the topic) |
| 4 | Soak 30 days with LIS-Sample at its current replica count (rollback = step 1 reversed) | weekly: input vs output counts, dead-letter 0, outbox unsent 0 |
| 5 | `SAMPLE_LEGACY_IMPORT_ENABLED=true` only after LIS-Sample's cron is off (or after confirming both services' `REDIS_URL` resolve to the same Azure cache db 0, which they do today) | 09:16 LA log "Start handling storage info from legacy system" on exactly one trans pod |

Rollback at any step: set the switch back to `false`, rollout restart. In-flight peekLock messages return to the queue after lock expiry (1 min) or auto-renew end (5 min); LIS-Sample's consumer picks them up. Known cost of every trans rolling restart: one duplicate `UPSERT_RACK` per in-flight message (benign for upsert subscribers; pre-existing in LIS-Sample).

Housekeeping: purge the 220 dead-lettered messages on `storage-info-updates` (all older than 7 days; the consumer would complete them untouched anyway).

## 7. Open items

- `enableShutdownHooks()` in trans `main.ts` — separate PR, staging first (changes shutdown ordering for every module).
- Service Bus staging entities — Tianhao / Alex, or Contributor for the agent account.
- Secret layout for prod vs st (shared `lis-trans-secret`).
- LIS-Sample consumer kill-switch PR (step 6.3) — owner to be decided.
- Main twin PR `feature/leo/VP-18481` (e2b4601) after the staging soak.
- Trans drops info-level logs: decide whether the consumer's start and per-message lines become `warn` in trans, or whether a Datadog metric replaces them (the runbook currently relies on DB and queue counters only).
