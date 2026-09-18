# Phase 1 Detail — Remove the Detours

**Parent:** Trans v1 / v2 Optimization — Phased Plan · **Epic:** VP-18260 · **Ticket:** VP-18262

Phase 1 deletes whole round trips rather than shaving milliseconds off existing ones. Every item is a call that leaves the cluster, or crosses a service, for no reason that still holds. Most of it is configuration, which is why it goes first: it is reversible in seconds, and a wrong value shows up immediately rather than subtly.

This doc is detailed enough to cut tickets from. Each work item below is one ticket.

---

## 1. Definition of done for the phase

- No response body, status code, or side effect changes anywhere. Class A and C rules from the plan apply per item.
- Every retargeted key keeps its previous value recorded, so rollback is a single `kubectl edit`.
- `cloud-local-proxy` has either a complete caller list or a dated path to one — it is not scaled to zero on an assumption.
- Every removed route is justified by **caller composition over the full log-retention window**, measured from request logs rather than sampled spans — not merely by a zero window. Where that evidence cannot reach (retention is 15 days, so a monthly caller is invisible), the gap is closed by an announced notice period, not by assuming absence.

> On that last point, from experience earlier in this program: spans are sampled — in one two-hour window, 976 real requests produced 4 spans (≈0.4%). Counting sparse events with spans understates them by two orders of magnitude. Trans v1 logs every request and response, and that is the instrument to count with. Error spans are near-complete (they are kept by an error retention filter), which makes the numerator trustworthy and the denominator not — so error *rates* must never be computed from sampled counts.

---

## 2. Already shipped in this phase

| Item | What changed | Evidence it was safe |
|---|---|---|
| **S1** — `checkIfPersonalizedReportCanBeCreated` | trans v2 addresses the report server directly instead of hopping through `cloud-local-proxy` | 58 real samples compared old path vs new inside a prod pod: status and body identical on all 58 (38 `false`, 20 `true`) |
| **S2** — kit / test-status / questionnaire | trans v2 calls gRPC directly instead of calling trans v1 over HTTP to reach the same gRPC service | Shipped behind `TRANS_PROXY_GRPC_MODE` with a shadow mode; switched to `grpc` 2026-09-16 22:03 UTC. Since the switch: 0 client-facing request errors, 0 pod restarts, 0 `DEADLINE_EXCEEDED`, and 1 gRPC error in 24.4 h that belongs to a pre-existing downstream class |
| **S6** — trans v1 dead config | 14 keys pointing at a retired cloud-proxy URL with 0 code reads, removed | grep proved 0 reads; removal ran staging-first |
| gRPC deadlines | Both services' core channels now have a real deadline; a retry policy that never applied was deleted rather than kept | — |

The flag branches from S2 stay in place for now. They are the rollback path, and deleting them trades a three-minute recovery for a redeploy. They come out in item **P1-F** once the gRPC path has held a normal week.

---

## 3. Work items

### P1-A — trans v1: replace public-ingress URLs with in-cluster service DNS

**Problem.** 55 keys in `lis-trans-config` address services that run in the same AKS cluster via `api.vibrant-wellness.com`. Each call leaves the cluster, crosses TLS termination, the WAF and the ingress, and comes back in. Measured cost is **0.8–3.8 s per call**. Affected targets: base-report, shipping, accounting, samples, interactive-report, charging.

**Why this is lower risk than it looks.** trans v2 already addresses the same services by `*.svc.cluster.local`. The target values are not guesswork — they exist, in production, working, in the sibling ConfigMap.

**Approach — one ticket per target service, six batches**, in this order (largest measured benefit first): base-report → shipping → accounting + charging → samples → interactive-report → remainder.

Per batch:
1. Take the in-cluster value from `lis-transv2-config` for the same target; confirm the Service and port exist.
2. Check what the public ingress does that an in-cluster call will not: injected auth headers, a required `Host`, TLS-only behavior on the target. **If the ingress is doing something the target depends on, that key stays on the ingress** and the reason is recorded — this is the one way this item can break production, and it breaks it as a 401 or a 500 on the first request.
3. Change on staging, compare responses on a fixed request set for that target's endpoints.
4. Change on prod with `kubectl edit`, previous value recorded in the ticket.
5. Watch that endpoint's p95 and error rate in Datadog for 24 h before the next batch.

**Affected components:** `lis-trans-config` (prod + staging) only. No code.
**Rollback:** restore the previous key value — seconds, one key.
**Size:** 6 batches × ~0.5 day = **3 days**.

### P1-B — trans v2: delete the 8 unread config keys

**Problem.** 8 keys in `lis-transv2-config` (`Get_Requisition`, `url_GenerateBatchReqOrReportV2` and 6 others) point at `192.168.10.153:8081`, an on-prem address that is not reachable from AKS at all. Code reads: **0**. They are the v2 equivalent of the 14 already removed from v1.

**Approach:** re-confirm 0 reads by grep at the current `main`, delete on staging, smoke test, delete on prod. **Verification:** the point of this ticket is that nothing changes; a diff of the ConfigMap plus a green smoke run is the whole proof.
**Size:** **0.5 day**.

### P1-C — retire the proxy routes that no longer have a caller

**Ticket: VP-18320** (announced 2026-09-18, removal 2026-10-02, due 2026-10-09).

**Problem.** `/proxy/grpc/*` in trans v1 exists so that trans v2 could reach gRPC services over HTTP. S2 removed that need. Counted from request logs across the full 15 days Datadog retains (2026-09-03 → 2026-09-18):

| Route | Daily rate before the cutover | 09-17 | 09-18 | Read |
|---|---|---|---|---|
| `getTestStatus` | 120–1,876, in lockstep with `getQuestionaireBySampleId` every single day | 0 | 0 | Retire |
| `getQuestionaireBySampleId` | same series, never differing by more than 1 | 0 | 0 | Retire |
| `listTnpCode` | 0, every day, including before the cutover | 0 | 0 | Retire |
| `getKitStatus` | ≈2× the above (239–3,700) | 15 | 5 | Keep — unidentified caller |
| `getPatientTestsResult` | 1–5, flat, unaffected by the cutover | 5 | 3 | Keep — pre-existing caller |
| `sendSkinPlacePatientOrders` | 0 (its known caller uses the on-prem proxy) | 0 | 0 | Keep — see P1-E |

**The lockstep is the evidence, not the zero window.** `getTestStatus` and `getQuestionaireBySampleId` track each other to within one call on every one of the 15 days, and `getKitStatus` runs at exactly twice their rate. That is one caller's fixed per-sample pattern — transv2's patientProfile — rather than a population of callers. A second, independent consumer would break the lockstep on the days it ran; it never breaks. Then both went to exactly zero the day after the cutover. Two zero windows alone would not have justified this; the shape of the 15 days does.

`listTnpCode` is the cleanest of the three on different grounds: zero traffic for the entire window *including before the cutover*, and no caller in any of the 63 repos on the dev machine. (`LIS-backend-results-grpc` implements `listTnpCode` — it is the downstream service, not a caller. Worth stating because it looks like a caller in a grep.)

**What this cannot see.** Log retention stops at 15 days — a 35-day query returns nothing before 2026-09-03, on flex storage too — and the code search only covers locally cloned repos. A caller running monthly is invisible to both. That gap is closed procedurally: a two-week announced notice with a named place to object (VP-18320), then a re-check of the logs on the removal date.

**Approach.** Remove the three route handlers and the matching config keys in both repos in one PR, so no key is left pointing at a route that no longer exists.
**Rollback:** revert the PR; the gRPC clients behind the routes are untouched.
**Size:** **0.5 day**, on 2026-10-02.

### P1-D — identify the client still calling `/proxy/grpc/getKitStatus` and `getPatientTestsResult`

**Problem.** A trickle of ~0.5 calls/hour survived the cutover. Four candidate explanations were checked and each is ruled out by evidence rather than by assumption:

1. trans v2's first call site returns the cached gRPC result when the mode is `grpc` and has **no HTTP fallback** (read at `origin/main`).
2. trans v2's second call site is mode-gated the same way; its gRPC branch never touches axios.
3. Config drift — the failure mode this program has seen before — is not it: `lis-transv2-config` reads `grpc`, and all three pods' `printenv` agree, across another team's deploy.
4. `cloud-local-proxy` mentions `/proxy/grpc` only in comments describing where code came from. It is not a caller.

So there is an unidentified in-cluster consumer (an `axios/1.16.0` client addressing `lis-trans-service:3146`). At this volume the requests are never sampled into a trace, so attribution cannot come from APM.

**Approach.** Log `user-agent` and `x-forwarded-for` on `/proxy/grpc/*` in the trans v1 proxy controller. Log-only, no behavior change, no response change. Observe for a week, then route the finding to whichever team owns the caller.

**One correction from the 15-day read.** `getPatientTestsResult` is not collateral from the cutover: its 1–5 calls a day are flat across the whole window and completely unmoved by the switch. It was never on the migrated path, and whoever calls it has been calling it for at least 15 days. `getKitStatus`'s residual is the same order of magnitude, so one client doing both remains the most economical explanation — but "the same caller as the migrated path" is now excluded rather than supported.

**Why it matters, and it is more than retirement.** Identifying the caller decides which of two end states each route gets. If the caller can speak gRPC, the route is deleted and the work consolidates internally — that path is proven, not theoretical: transv2's PR #629 did exactly this, carrying over both the metadata construction and the proto3 `packages` normalisation line by line. If the caller cannot (a service that cannot vendor the proto, an on-prem script, someone else's scheduler), the route stays as that caller's bridge. `sendSkinPlacePatientOrders` is already the second case, pointing the other way: billing moves *onto* trans v1, which makes trans v1 the consolidation point rather than a removal candidate.

So the end state is not six routes disappearing. It is five disappearing and one becoming where the others consolidate. This is also the blocker for the `cloud-local-proxy` scale-to-zero, and the cheapest way to get the answer — the alternative is ingress logs from a cluster this team has no access to.
**Size:** **0.5 day** of work, then a week of waiting.

### P1-E — `cloud-local-proxy` retirement

**Problem.** Built in 2023 to cross an Azure ↔ on-prem network split that has since been closed. Still running: 3 replicas on `:latest`, no probes, not in any CI/CD pipeline — the cloud copy is pushed by hand. All 18 of its routes already have equivalent implementations in trans v1 (and the trans v1 versions of `/old-report/*` additionally carry the PHI ownership gate added under VP-17284, which the proxy's copies do not).

**Remaining work, in order:**
1. Pull ingress access logs for both `api.vibrant-america.com/v1/lis/cloud-proxy` (cloud) and `www.vibrant-america.com/lisapi/v1/lis/cloud-proxy` (on-prem) and enumerate callers. **The on-prem side needs Ray** — no access from here.
2. Repoint `LIS-backend-billing`, which has `.../cloud-proxy/grpc/sendSkinPlacePatientOrders` hard-coded at `ProZOrderServiceImpl.java:115`, to the trans v1 equivalent. Separate team, separate ticket; this side has read-only access to that repo. The on-prem proxy cannot be scaled to zero until this lands.
3. Scale to zero in both clusters after 30 days at zero traffic; delete later.

**Clock:** the known cloud-side caller was removed on 2026-09-14, so the earliest cloud scale-to-zero is **2026-10-14**, and only if step 1 turns up nothing else.
**Size:** ~1 day on the trans side; the rest is coordination and waiting.

### P1-F — remove the superseded flag branches and stale keys

**Problem.** After a cutover holds, its old branch is dead weight that still has to be read and maintained.

**Approach.** Once the gRPC path has held for a normal working week (i.e. from **2026-09-23**), delete the `http` and `shadow` branches of `TRANS_PROXY_GRPC_MODE` along with the now-stale `proxy_*` config keys in trans v2.

**Explicitly not in scope:** `TRANS_TIMELINE_KIT_MODE` stays in `shadow`. That cutover is **declined, not deferred** — reopening it needs proof that the two paths read the same record (provenance), not a longer shadow run. A longer run only amplifies the same inference.
**Size:** **0.5 day**. **Depends on:** P1-C.

---

## 4. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| An in-cluster target depends on something the public ingress injects (auth header, TLS, `Host`) | That endpoint returns 401 or 500 on the first request after the change | Step 2 of P1-A is exactly this check; staging first; one batch at a time with 24 h of observation between |
| A ConfigMap change is reverted by someone running `kubectl apply -f` from the repo copy | Phase 1's gains silently disappear | The repo copy holds 5 keys against 154 live — it must never be applied. Drift detection is a Phase 0 item; until it exists, this is a team convention and a known hole |
| `cloud-local-proxy` has a caller nobody has found | Scaling to zero breaks another team's service | P1-E step 1 gates the scale-to-zero; the 30-day zero-traffic clock runs after the caller list, not instead of it |
| A retired route turns out to have a rare caller (monthly batch, scheduled job) | A 404 on a path that used to work | The one class the logs cannot see, since retention is 15 days. Closed procedurally rather than empirically: a two-week announced notice with a named place to object (VP-18320), and a re-check of the logs on the removal date |
| Deleting a flag branch removes the rollback path for a recent cutover | A regression needs a redeploy instead of a config flip | P1-F is dated a week after the cutover, not immediately |

---

## 5. Sizing

| Item | Size | Gated on |
|---|---|---|
| P1-A — in-cluster DNS, 6 batches | 3 d | — |
| P1-B — v2 dead keys | 0.5 d | — |
| P1-C — retire 2 proxy routes | 0.5 d | — |
| P1-D — identify remaining caller | 0.5 d + 1 week observing | — |
| P1-E — `cloud-local-proxy` retirement (trans side) | 1 d | Ray (on-prem logs), billing team (repoint) |
| P1-F — remove superseded branches | 0.5 d | P1-C, and a week of stability |

**Total trans-side: ~6 dev-days.** Two items finish on other teams' calendars, which is why the phase's dev-complete target (2026-10-02) covers the trans-side work and not the `cloud-local-proxy` deletion itself.

---

## 6. Tickets to create

- `[Trans Opt][P1] trans v1: replace public-ingress URLs with in-cluster service DNS — base-report`
- `[Trans Opt][P1] …— shipping`
- `[Trans Opt][P1] …— accounting + charging`
- `[Trans Opt][P1] …— samples`
- `[Trans Opt][P1] …— interactive-report`
- `[Trans Opt][P1] …— remaining targets`
- `[Trans Opt][P1] trans v2: remove 8 unread config keys pointing at an unreachable on-prem address`
- ~~`[Trans Opt][P1] trans v1: retire /proxy/grpc/getTestStatus and /proxy/grpc/getQuestionaireBySampleId`~~ → created as **VP-18320**, widened to include `listTnpCode`
- `[Trans Opt][P1] trans v1: log user-agent and x-forwarded-for on /proxy/grpc/* to identify the remaining caller`
- `[Trans Opt][P1] cloud-local-proxy: enumerate callers from cloud and on-prem ingress access logs`
- `[Trans Opt][P1] LIS-backend-billing: repoint sendSkinPlacePatientOrders from cloud-proxy to trans v1` (other team)
- `[Trans Opt][P1] cloud-local-proxy: scale to zero after 30 days at zero traffic`
- `[Trans Opt][P1] trans v2: remove the http/shadow branches of TRANS_PROXY_GRPC_MODE and the stale proxy_* keys`
