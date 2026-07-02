# Performance Self-Review — EMR Integration & Reliability (2026 H1)
**Owner:** Hung-Fan Lin (Leo)  ·  **Window:** ~2025-12-29 → 2026-06-29  ·  **Compiled:** 2026-06-29

> Sourcing convention: every number cites where it comes from —
> `[STM:<file>]` = lis-code-agent short-term-memory record,
> `[KB:<file>]` = lis-code-agent knowledge base,
> `[Jira]` = Jira JQL query, `[computed]` = my arithmetic over sourced per-item numbers (not a single source).
> Items with no substantiating number are marked **(no quantified data)**.
> A "**NEEDS YOUR INPUT**" list at the end flags figures you asked for that are **not** in any source I scanned — do not quote those until you confirm them.

---

## Executive summary

Over 2026 H1 I owned EMR-integration delivery and production reliability for the LIS platform: onboarding/expanding EMR integrations, a major order-routing cutover, and front-line incident response for the HL7 order-intake and result-transmission pipelines.

- **Throughput:** 123 tracked work records `[STM: directory count]`; ≥100 Jira tickets assigned & updated in the window `[Jira]`.
- **Largest engineering change:** order-resolution cutover from `order_clients` → `ehr_integrations` as the canonical gate — 225 rows backfilled + 730 updated, 100% verified, zero regression `[STM: VP-16968]`.
- **Incident response:** 7 production incidents diagnosed/resolved `[STM: INCIDENT-* files]`, including a 19.5-hour HL7-fetch outage, a service-wide SFTP deadlock, a 990-record HL7 timestamp corruption, and a vendor-reported 20-stale-connections/day leak — each with before/after prod evidence.

---

# Part 1 — Accomplishments by theme

## Theme 1: Order-intake & routing pipeline cutover (highest-impact change)

### VP-16968 — Make `ehr_integrations` the order-routing gate (replacing `order_clients`)
- **(1) Problem/background:** When emr-v2 created an `ehr_integrations` row, the `ordering/result/sftp_enabled` flags did not track `integration_type` (DTO defaulted them false), so "API create succeeded ≠ integration works." The real order admission gate was still the legacy `order_clients` table; the `ehr_integrations` query was logging-only. `[STM: VP-16968]`
- **(2) What I did / technical approach:**
  - Prod data fix: corrected **32** `type↔flag` mismatches (guarded `WHERE api_enabled=1 AND sftp_enabled=0` returned 0 rows → safe) with a derivation rule (ORDER_ONLY=o1/r0/s1, RESULT_ONLY=o0/r1/s1, FULL=o1/r1/s1). `[STM: VP-16968]`
  - Code: added `deriveCapabilityFlags` in `integration-type-validation.util.ts`; added `kits_options`/`old_clinic_id` columns to `ehr_integrations`; rewrote `customer-detail-fetcher.service.ts` so the gate = `status='LIVE' AND ordering_enabled=true`, with multi-row precedence FULL > ORDER_ONLY > other, then `updated_at` DESC. `[STM: VP-16968]`
  - Backfill: **225** `order_clients` customers had no `ehr_integrations` row (23.6% of 955) → inserted 225 (FULL/LIVE), and updated **730** existing rows (kits/old_clinic). `[STM: VP-16968; KB: emr-integration.md:206]`
- **(3) Systems / stack:** lis-backend-emr-v2 (NestJS + Prisma, MySQL `lis_emr`), gRPC customer lookup, HL7 order-intake processor (`hl7-order.processor.ts`).
- **(4) Quantified impact:**
  - **225 inserted + 730 updated rows, 100% row-by-row verified, 0 mismatches** `[STM: VP-16968]`
  - **Zero regression** confirmed: all 225 ORDER_ONLY customers had never appeared as `result_client_id` in `result_transmission_records` (24,530 rows), proving they never used the v2 result pipeline `[STM: VP-16968]`
  - Post-deploy on-prem: **no cutover-related errors** (CustomerDetailFetcher / ehr_integrations / P2000) observed `[STM: VP-16968, 2026-06-12]`

---

## Theme 2: EMR integration onboarding & bidirectional expansion

> Pattern work: new-clinic onboarding, same-practice provider adds, admin-portal "stub finalize", and RESULT_ONLY → FULL_INTEGRATION upgrades — across Cerbo/MDHQ, Optimantra, and Follow-That-Patient vendors. All executed as single guarded Prisma `$transaction`s with in-transaction verification. `[STM: per ticket]`

| Ticket | Scope | Quantified | Source |
|---|---|---|---|
| VP-16720 | Follow-That-Patient → bidirectional | **24 (clinic,customer) pairs** all FULL/LIVE; 18 upgraded, 3 inserted; order_clients deduped to **21 distinct customers** | `[STM: VP-16720]` |
| VP-16423 | Cerbo new — Alive+Well Austin | 7 providers / 1 practice (7 ehr_integrations + 7 order_clients) | `[STM: VP-16423]` *(no impact metric)* |
| VP-17136 | Follow-That-Patient — +6 locations | 8 integrations (5 new clinics + 3 providers); 1 upgraded RESULT_ONLY→FULL | `[STM: VP-17136]` |
| VP-16245 | Cerbo — Alpine Wellness | 2 providers; upgrade + folder-path rollback (5 rows) | `[STM: VP-16245]` |
| VP-16280 / VP-16766 / VP-16734 / VP-16396 / VP-16424 / VP-16617 | single-provider adds / stub finalizes / RESULT_ONLY→FULL upgrades | 1 provider each | `[STM: per ticket]` *(no impact metric)* |

- **Onboarded/expanded provider–practice pairs (sum of the per-ticket counts above): ≈ 44** `[computed from STM per-ticket counts — not a single source]`
- **Data-integrity catch (VP-16245):** detected a vendor↔PM folder-path mismatch (`/acw` vs actual `/awc`) by directly inspecting the SFTP server, then atomically rolled back 5 SQL rows. Verified **0 inbound/outbound records lost** for clinic 11372 during the window. `[STM: VP-16245]`
- **(3) Systems / stack:** lis-backend-emr-v2 (Prisma/MySQL), vendor SFTP (Cerbo/MDHQ client-specific folders; Optimantra & FTP vendor-shared folders), gRPC customer resolution (handles admin accounts with no real NPI).

---

## Theme 3: Knowledge consolidation & process

- Authored/maintained the EMR-integration knowledge base (`emr-integration.md`, ~1000 lines) consolidating patterns from 50+ tickets: stub-finalize flow, `kit_delivery_option` alignment, sibling-row borrow semantics, MDHQ folder-path bugs. `[KB: emr-integration.md]`
- Established the canonical order-customer-resolution rule (ORC.12 NPI → `ehr_integrations` winner, not `order_clients`) now captured as a reusable skill. `[KB: emr-integration.md]`
- **(no quantified data)** — process/enablement value; impact is reduced manual error rate (not separately measured).

---

# Part 2 — Production incident self-evaluation

> 7 incident records in 2026 H1 `[STM: INCIDENT-* files]`. Causation stated honestly (vendor-side / infra-side / regression from a prior change) — pick which to feature.

### INCIDENT-20260604 — MDHQ stale SFTP connections (~20/day)  ·  *clean win*
- **Root cause:** The HL7-fetch cron connects per-folder; MDHQ owns 172/196 folders, so it ran **172 connect/disconnect × 96 ticks/day = 16,512 SSH sessions/day** `[computed in STM: INCIDENT-20260604]`. On disconnect, when MDHQ's Bitvise WinSSHD throttled and withheld the SSH_MSG_DISCONNECT ACK, the 5s-timeout fallback called `socket.destroy()` **without sending TCP FIN** → the peer's session lingered in ESTABLISHED until OS keepalive (~2h). ≈0.12% of sessions × 16,512 ≈ **20 lingering/day**, matching MDHQ's report. `[STM: INCIDENT-20260604]`
- **How I diagnosed it:** `kubectl exec` egress-IP verification (confirmed pod = 45.24.217.146); `kubectl get pod` (confirmed v1 pods scaled to 0, so it was v2); `sftp_folder_mapping` query (MDHQ = 172 folders); prod-log rate `grep -c 'Connecting to SFTP server: 34.199.194.51'` ≈ 172/15min. `[STM: INCIDENT-20260604]`
- **Fix:** 3-stage `forciblyClose()` teardown — bounded `client.end()` → socket FIN + drain wait → `resetAndDestroy()` (guaranteed RST); wired `OnApplicationShutdown`/`OnModuleDestroy` + SIGTERM; per-disconnect `[SFTP_CLOSE]` structured log; 9 unit tests. `[STM: INCIDENT-20260604]`
- **Before/after (prod):** before — MDHQ reports 20 stale/day. After (24 ticks, 2026-06-04 22:00–23:50 UTC): **graceful 1939 (99.4%)**, econnreset 10 (0.5%), `fin_then_rst` **1** (0.05%), all other failure outcomes **0**; **0 ESTABLISHED sockets persisted across cron windows**. Leo confirmed resolved end-to-end (pod + MDHQ side) on 2026-06-08. `[STM: INCIDENT-20260604]`

### INCIDENT-20260601 — SFTP singleton deadlock hang  ·  *clean win*
- **Root cause:** `SftpConnectionService.safeDisconnect()` did `await client.end()` with **no timeout**. The service is a NestJS singleton shared by the fetch cron, the BullMQ result workers (concurrency=3), and all gRPC callers; when a vendor (MDHQ throttled) never ACKed the disconnect, the await hung forever, `finally` never ran, the client ref was never cleared, and every subsequent caller blocked on the same await → **service-wide deadlock**. `[STM: INCIDENT-20260601-sftp-hang]`
- **How I diagnosed it:** pod logs (last line always `HL7 fetch complete: 0 file(s)`, then 6–13 min silence); pod health normal (CPU 77m / mem 219Mi) ruling out resource exhaustion; BullMQ queue stats (stuck jobs). `[STM: INCIDENT-20260601-sftp-hang]`
- **Fix:** `Promise.race` + 5s timeout + force-destroy socket, clearing the ref **before** the await. Immediate mitigation: `kubectl rollout restart deployment lis-emr-v2-deployment-prod` (2026-06-01 ~10:16 PDT). `[STM: INCIDENT-20260601-sftp-hang]`
- **Before/after:** before — a 157-sample batch stuck at **116/157**, **10 PENDING BullMQ jobs** permanently stuck; restart restored processing; the timeout patch removed the deadlock class. `[STM: INCIDENT-20260601-sftp-hang]`

### INCIDENT-20260528 — 19.5-hour HL7-fetch outage (redlock lock-leak)
- **Root cause:** After I enabled v2 for all vendors (`UPDATE sftp_folder_mapping SET use_v2_pipeline=1`, 196 rows), 24 never-before-v2 vendor hosts entered the fetch loop. `Hl7OrderFetchService.handleCron` had **no hard timeout**; an SSH `client.list('.')` validation stalled on MDHQ's 172-subdir home dir → `runIngestion` never returned → redlock auto-extend held the lock forever → every 15-min tick skipped ("lock held") → **19.5h of zero fetch**. *(Triggered by my own enable-all change exposing a missing timeout.)* `[STM: INCIDENT-20260528]`
- **How I diagnosed it:** `hl7_file_input` last-row timestamp (2026-05-27 22:48:37 UTC) to pin the stop; `emr_sftp_source` table (found PF on non-standard port 2222); `nc -z host port` reachability; pod-log "lock held" pattern. `[STM: INCIDENT-20260528]`
- **Fix (PR #135):** `MAX_RUN_DURATION = 13min` (< 15min cron), `PER_FOLDER_TIMEOUT = 2min`, `runWithTimeout` helper, `forceReleaseTimer` failsafe + `releaseOnce` dedupe, force-disconnect on per-folder timeout; both env-overridable. `[STM: INCIDENT-20260528]`
- **Before/after (prod):** before — 5/28 = 19 rows, 5/29 = 1 row (service dead). After (first fix tick 21:45 UTC): full 196-folder scan in **7m20s**, per-folder timeout correctly isolated the hung MDHQ folder, other 195 processed; next tick **6m17s, 0 timeouts**. `[STM: INCIDENT-20260528]`

### INCIDENT-2604156666 — 990 HL7 results with corrupted `0001-01-01` timestamps (regression)
- **Root cause:** A 5/18 deploy (c0852d0) switched the v2 Go gRPC service to primary. For missing `sample_collection_time`, the Go service serialized the `time.Time{}` zero value `"0001-01-01T00:00:00Z"` (v1 Java returned `""`); emr-v2's `getValidCollectionTime` validation (empty / NaN / year>earliest-approval) didn't catch year-0001, so `00010101000000` was written into OBR-7/OBR-14. *(Regression from the v2-primary switch.)* `[STM: INCIDENT-2604156666]`
- **How I diagnosed it:** DB-only diagnosis script (`_diagnose-2604156666-db.ts`) comparing `emr_sample` correct values vs `generated_hl7_content`; raw gRPC capture from both v2 (10.224.0.199:32100) and v1 (192.168.60.6:30276) showing zero-value vs correct; per-OBR field inspection; `kubectl exec`. `[STM: INCIDENT-2604156666]`
- **Fix:** reverted the v2-primary switch for sample/patient/clinic/order steps (kept the cloud→on-prem fallback wrapper, and cloud fallback for the testresult step per VP-16685); added 6 missing unit tests. `[STM: INCIDENT-2604156666]`
- **Before/after (prod):** **990 records** affected from 5/19 (vs 39 baseline in the prior 6 weeks — ~25× spike) across **14 vendors** (MDHQ 482, ATHENA 88, POWER2PRACTICE 85, PF 74, OPTIMANTRA 71, Elation 47, ChARM 46, FollowThatPatient 40, THM 22, ECW 14, OptimalDX 12, DocVilla 5, HealthMatters 2, Cascades 2). Re-push over 5 runs: **754/1004 vendors got the fixed copy (75.1%)**; remaining 250 blocked by SFTP-layer failures (handshake timeouts). `[STM: INCIDENT-2604156666]`

### INCIDENT-20260518 — Result-generation pipeline stalled by Azure Redis outage (infra)
- **Root cause:** Azure Redis (`vibrant-cloud-cache...`) became DNS-unreachable from pods; a v1 gRPC ReferenceRange call hung with no timeout; worse, on failure emr-v2 **fabricated fake barcodes/Unknown-Patient and shipped 552-byte junk HL7** to customer SFTP. `[STM: INCIDENT-20260518]`
- **How I diagnosed it:** `grpcurl` isolation of each RPC endpoint (cloud vs on-prem); pod-log grep (128× `getaddrinfo ENOTFOUND` in 10 min); wellness PDF endpoint real-vs-fake comparison (9.6MB ✓ vs 87 bytes ✗); BullMQ `LLEN`/`processedOn` stats. `[STM: INCIDENT-20260518]`
- **Fix:** cloud-primary/on-prem-fallback for steps 1–5, 30s deadline on the v1-only reference-range step, **removed the fake-data fabrication** (now marks `GENERATION_ERROR`), BullMQ hard 10-min `Promise.race` timeout, concurrency **1→3**, widened gRPC retry conditions. `[STM: INCIDENT-20260518]`
- **Before/after:** before — BullMQ peak backlog **184 jobs** (1 active + 183 waiting); one sample stuck 5+ hours at progress=10. After — isolation tests pass (e.g. testresult 1s/324 tests; real PDF 200 OK 9.6MB); auto pipeline recovered. *(No "queue-drain duration" number recorded.)* `[STM: INCIDENT-20260518]`

### INCIDENT-20260529 — MDHQ SFTP auth rejection (vendor-side) + order_clients↔ehr_integrations sync
- **Root cause:** MDHQ began rejecting auth at 11:16 UTC (TCP open via `nc`, but SSH handshake closed by server; password + paramiko both rejected) → vendor-side change (IP allow-list / credential rotation). Correctly diagnosed as **not ours** → did not rollback. `[STM: INCIDENT-20260529]`
- **How I diagnosed it:** `nc -zv 34.199.194.51 2210` from prod IP (TCP ok); ssh2-sftp-client + paramiko auth tests (both fail); verified 16 other shared-vendor connections all OK; per-vendor connection stats (MDHQ 223 fail / non-MDHQ 21 OK in one tick). `[STM: INCIDENT-20260529]`
- **Quantified (the sync sub-task):** UPDATE **828** rows (customer/clinic match) + **1** missed row found via reverse-audit (customer 508387, NPI NULL both sides) = **829** set to FULL_INTEGRATION+1; **100% row-by-row verified, 0 mismatch**, ehr_integrations total 1022 unchanged. `[STM: INCIDENT-20260529]`

### INCIDENT-20260601-followup-sftp-verify — post-timeout file verification (deferred)
- Identified that a 10-min SFTP upload timeout can mark a file `TRANSMISSION_ERROR` when it actually landed (slow vendor ACK; e.g. sample 2560935 9MB Athena upload present in `/inboundintoathena/`). Designed an `stat()`-verify fix; **deferred** pending a >5-samples/week trigger. `[STM: INCIDENT-20260601-followup]`

---

# Part 3 — Hard numbers (with sources)

### Throughput / tickets
| Metric | Value | Source |
|---|---|---|
| Tracked work records (STM) | **123** (VP 85 / QH 26 / INCIDENT 7 / LBS 3 / other 2) | `[STM: directory count]` |
| Records tagged `emr_integration` | **48** | `[STM: frontmatter grep]` |
| Records tagged `technical` | **76** | `[STM: frontmatter grep]` |
| Jira tickets assigned & updated in window | **≥100** (first 100-page capped; more exist) | `[Jira]` |
| — of most-recent 100: Done | **82** | `[Jira]` |
| — of most-recent 100: EMR/HL7/integration keyword in title | **57** | `[Jira]` |
| — by project (most-recent 100) | VP 85 / QH 10 / LBS 5 | `[Jira]` |
| Production incident records | **7** | `[STM: INCIDENT-* files]` |

### Platform / ecosystem scale
| Metric | Value | Source |
|---|---|---|
| Company repos (org) / actively-developed | **153 / 31** | `[KB: repo-catalog.md:143]` |
| Public EMR vendors integrated | **18** (+15 private) | `[KB: emr-integration.md:519]` |
| `ehr_integrations` rows (full-table, 2026-05-06) | **1015** | `[KB: emr-integration.md:280]` |
| Distinct `order_clients` customers | **955** (~225 / 23.6% had no ehr_integrations) | `[KB: emr-integration.md:206]` |
| Specialty test panels (product) | **60+** | `[KB: business-model.md:104]` |
| emr-v2 stack | NestJS / MySQL `lis_emr` / Prisma / Kafka / BullMQ; HTTP 3000, gRPC 5000 | `[KB: repos.md:223]` |
| Java EMR-Backend v1 fully retired | **2026-06-10** (all EMR orders on v2) | `[KB: repos.md:241]` |

### Reliability / performance figures established
| Metric | Value | Source |
|---|---|---|
| MDHQ SSH sessions/day (pre-fix) | **16,512** (172 folders × 96 ticks) | `[computed in STM: INCIDENT-20260604]` |
| Graceful-teardown rate after fix | **99.4%** (1939/~1950 over 24 ticks) | `[STM: INCIDENT-20260604]` |
| Longest outage resolved | **19.5 h** (INCIDENT-20260528) | `[STM: INCIDENT-20260528]` |
| Fetch-tick time after fix | **6–7 min** for 196 folders | `[STM: INCIDENT-20260528]` |
| Peak BullMQ backlog handled | **184 jobs** | `[STM: INCIDENT-20260518]` |
| Result-gen concurrency change | **1 → 3**, 10-min hard timeout | `[STM: INCIDENT-20260518]` |
| HL7 corruption blast radius fixed | **990 records / 14 vendors** | `[STM: INCIDENT-2604156666]` |
| Order-routing backfill verified | **225 insert + 730 update, 100%** | `[STM: VP-16968]` |

---

## ⚠️ NEEDS YOUR INPUT — figures you asked for that are NOT in any source I scanned
**Do not quote these until you confirm them from a real source (DB query / dashboard / Grafana).**

1. **"40+ microservices platform"** — not substantiated. The closest sourced facts are **153 org repos / 31 actively-developed** `[KB: repo-catalog.md:143]`. If by "microservices" you mean the Go v2 financial + NestJS core services, that's roughly 30–40 *main* services, but no source states "40+". Recommend rephrasing to the sourced "153-repo / 31-active platform" or confirm a real service count.
2. **Daily order / sample volume** — not found in any record. (Files mention SFTP folders, `hl7_file_input`, `emr_sample`, but no daily count.)
3. **Provider / clinic / patient totals** — not found. Closest: 955 distinct order-client customers, 31 active clinics — but no patient or full provider/clinic totals.
4. **End-to-end latency / SLA (median or p95)** — not found. Only per-operation timeouts exist (10-min result-gen, 180s PDF, 13/15-min SFTP fetch).
5. **QPS / throughput-per-second** — not found (only LIS-Shipping rate-limit 3000/60s and result-gen concurrency=3).

---

### Notes for editing this draft
- Two incidents (20260528, 2604156666) were **regressions from my own change** (enabling v2 broadly / switching v2 gRPC primary). I've stated that honestly; decide whether to feature them as "diagnosed & resolved fast" or omit.
- The "≈44 provider–practice pairs" figure is **my sum of per-ticket counts**, not a single source — keep the per-ticket table if a reviewer asks for the breakdown.
