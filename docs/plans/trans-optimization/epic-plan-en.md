# Trans v1 / v2 Optimization — Phased Plan

**Epic:** VP-18260 · **This half:** VP-18262 (Leo) · **Twin half:** VP-18261 (Yekai) · **Reference model:** VP-17348 (Core V1 → V2)

This is the combined direction for the trans optimization: what the phases are, why they are in this order, and what each is aiming at. Phase 1 has its own detailed doc — [Phase 1 Detail — Remove the Detours](https://vibrantamerica.atlassian.net/wiki/spaces/LIS/pages/2696740867) — with scope, approach, risks and sizing, at the level needed to cut dev tickets. Later phases stay high-level until we reach them, the same way the Core migration epic was scoped.

The proxy layer specifically has its own page: [Retiring /proxy and cloud-local-proxy — Classification and Migration Targets](https://vibrantamerica.atlassian.net/wiki/spaces/LIS/pages/2697166874) assigns every route that is still in use to a target home and a downstream owner, and states what each wrapper adds that a migrating caller has to bring with it.

Two notes on what this page is and is not. It is the plan half of the joint deliverable: the investigation behind it is the trans v1 / v2 read, the Datadog measurements, and the AKS inventory done under VP-18262 between 2026-09-11 and 2026-09-18. Yekai's investigation under VP-18261 is still open and merges into the same phases — where it lands differently, this page gets updated rather than forked. Separately, some of what is described below has already shipped; that is deliberate and is marked per item, because measuring against real traffic is the only way the ordering below could be justified at all. What shipped, and what it measurably did, is recorded change by change on [Shipped Changes & Measured Impact](https://vibrantamerica.atlassian.net/wiki/spaces/LIS/pages/2684321795).

---

## 1. What trans is for — constraints the plan may not optimize away

1. **Trans is the only HTTP egress for PHI.** Core is becoming pure gRPC for security reasons, so anything outside the cluster that needs PHI comes through trans.
2. **Trans aggregates for the front end.** One call in, many downstream calls out, one response back.

Both survive every phase below. A change that moves PHI egress elsewhere, or pushes aggregation onto the client, is out of scope regardless of how much latency it would save.

---

## 2. The problem, as measured rather than as reported

The kickoff described "10–20 APIs over 2 s, worse at peak". Measured over 7 days against trace metrics — 100% of requests, not sampled spans — **11 endpoints exceed a 2 s p95 with at least 100 hits**: 9 trans v1 REST, 1 trans v1 gRPC, and trans v2 GraphQL (worst operation `PatientProfileSlow`, p95 3,101 ms).

**Peak hour is not the cause.** For the top 10, peak-hour p95 sits within ±5% of the whole-week p95. The latency is structural, so the fix is structural rather than capacity.

Three structural causes, in the order of how much they cost:

| # | Cause | Evidence |
|---|---|---|
| 1 | **Detours** — trans reaches same-cluster services the long way round | 55 trans v1 config keys address same-cluster services over the public ingress (0.8–3.8 s per call); trans v2 called trans v1 over HTTP just to reach a gRPC service it already has a client for; both services still routed through `cloud-local-proxy`, built in 2023 for a network split that was closed years ago |
| 2 | **Fan-out against core** — N+1 gRPC and serial pipelines whose steps are independent | `patientTestResultnewrange` issued 365 `GetPatientDetailedReferenceRangeInOut` calls in one request; `findPatient` ran seven independent stages in series; `patientProfile` fetched the same sample's kit four times |
| 3 | **No safety net** — "no behavior change" could be asserted but not demonstrated | Neither repo ran tests or typecheck anywhere in the deploy path; a push to `main` built and rolled the AKS deployment directly. Local baselines were red in both repos (v1 17/46 suites, v2 7/52) |

A fourth cause is real but sits outside trans and is called out as such throughout: the slowest endpoints on the list (three PDF routes at 11–14 s p95, `dashboard/user/timeline` at 2.9 s) spend their time in `lis-order`, `pdf-engine` and `lis-dashboard`. Trans is the proxy, not the cost. Those route to their owning teams rather than being patched here.

---

## 3. The rule every phase works under

**Zero functional change.** Every change must be able to show that the response and the side effects are the same, or it does not ship. Concretely:

- **Changes are classified**, and the class sets the proof required. **A** — config only (retarget a URL, delete an unread key): staging first, response comparison, keep the old value for one-key rollback. **B** — infrastructure only (resources, probes, image pinning): watch p95 and error rate. **C** — code with unchanged semantics (serial → parallel, drop a hop, dedupe within a request, cache): shadow diff plus unit tests plus a staging p95 comparison. **D** — contract change (response fields, error codes, endpoint removal): **not in this program**; it needs a product ticket and a front-end change.
- **Measure before touching.** No endpoint is picked without a p95 × volume ranking, and every ticket records the before number, the target, and the query used.
- **One ticket, one PR, and no further commits onto a PR once it is open.**
- **Every change carries a kill switch** — the old config value, or an env flag.
- **Parallelizing may not change error semantics.** Downstream calls that individually swallowed their errors keep doing so (`Promise.allSettled`); calls where one failure failed the whole request keep that too (`Promise.all`). Stated explicitly per ticket.
- **No DB schema changes, and no touching the PHI ownership gates** added under VP-17284. Removing a hop may never route around one.
- **ConfigMaps are edited in place** (`kubectl edit` / `patch`), never `kubectl apply -f` from a local file. The repo's copy holds 5 keys against 154 on the cluster; applying it is what has repeatedly reverted cloud URLs back to on-prem.

---

## 4. The phases

| Phase | Aim | Why it sits here | Status |
|---|---|---|---|
| **0 — Measurement and safety nets** | A ranking to work from, and an automated red/green that a deploy respects | Nothing after it can claim "no behavior change" without it. Costs nothing in risk: it changes no production behavior | **Mostly shipped** |
| **1 — Remove the detours** | Delete whole round trips at the config and routing layer | Best win per unit of risk in the program: mostly config, instantly reversible, and it removes latency rather than shaving it. Also the prerequisite for retiring `cloud-local-proxy` | **Partly shipped; the rest is the detailed doc** |
| **2 — Hot endpoints: parallelize and dedupe** | Take the measured top endpoints down without rewriting them | Needs Phase 0's net and Phase 1's simplified call graph first — parallelizing a call that is about to be deleted is wasted work | **Partly shipped** |
| **3 — Core v1 retirement alignment** | Trans stops using core v1 HTTP | Externally dated, not ours: core deletes those routes on 2026-10-31. Runs in parallel with 1 and 2 rather than queueing behind them | **Not started; blocked on core** |
| **4 — Infrastructure and resilience** | Resource requests/limits, HPA, uniform gRPC channel settings, logging cost | Independent of the code work, so it can run alongside Phase 1 | **Partly shipped** |
| **5 — Pass-through endpoint retirement** | Remove trans endpoints that only forward, and settle where `web-homepage-api` lives | Last, because it needs front-end changes and a PM decision — the only phase that touches the external contract | **Not started** |

### Phase 0 — Measurement and safety nets

Shipped: the p95 × volume ranking of both services (7 days, trace metrics); green unit-test baselines in both repos (v1 16 red → 58/58, v2 10 red → 54/54); and a typecheck + test gate in front of both deploy pipelines, running on every PR as well as on `main`.

The gate earned its keep on the first run by catching three failures that do not reproduce locally, and the fix — heap headroom rather than a tighter worker cap — cut the suite from 1,636 s to 92 s in v2 and 1,031 s to 63 s in v1. Cost is about +3 minutes per deploy.

Remaining: contract snapshots (v1 Swagger, v2 `schema.gql`) diffed in CI; a ConfigMap baseline with drift detection; a record/replay harness for shadow diffs; k6 scripts for a repeatable staging p95.

**One item needs a human, not a ticket:** branch protection on `main` has to mark the test job as a required status check in both repos. Until then a red PR check is advisory, and a merge to `main` is a deploy.

### Phase 1 — Remove the detours

Shipped: the personalized-report check now addresses the report server directly instead of going through `cloud-local-proxy`; trans v2's kit / test-status / questionnaire lookups call gRPC directly instead of going through trans v1's HTTP proxy; trans v1's 14 dead cloud-proxy config keys are gone; and both cutovers shipped behind flags with a shadow mode that compared old and new on real traffic before the switch.

Remaining, and the subject of the detailed doc: the 55 public-ingress keys in trans v1, trans v2's 8 unread keys, retiring the proxy routes that are now provably unused, identifying the one caller still using the rest, and the `cloud-local-proxy` retirement itself.

### Phase 2 — Hot endpoints: parallelize and dedupe

Four methods only, and no rewrites: serial → parallel where the steps are independent; N+1 → an existing batch API (if the downstream has no batch API, the item is dropped rather than the downstream changed); dedupe repeated identical calls within one request; and short-TTL cache only where a cache already exists on that path.

Shipped so far — four endpoints, measured on matched business-hour windows on consecutive weekdays:

| Endpoint | p50 before → after | p95 before → after |
|---|---|---|
| `POST /utility/createPatient` | 3.68 s → 2.08 s (−43%) | 3.70 s → 2.50 s (−32%) |
| `GET /trans/patientTestResultnewrange` | 2.17 s → 1.76 s (−19%) | 3.16 s → 2.76 s (−13%) |
| `POST /trans/getTimeLine` | 2.14 s → 1.78 s (−17%) | 2.42 s → 2.04 s (−16%) |
| `POST /trans/findPatient` | 1.01 s → 0.93 s (−8%) | 2.31 s → 1.88 s (−18%) |

Error rates did not move on any of the four.

Remaining, in rough value order: `GET /utility/getSetting` — 310,636 hits in 7 days, 38% of trans v1's useful traffic, nine fixed core gRPC calls per request, and an amplifier (one PDF triggers four calls to it, so 37 core gRPC calls); the trans v2 PNS resolver — 19 `@ResolveField`s each fetching independently, with no DataLoader anywhere in the repo; and the remaining serial work in `getTimeLine`.

### Phase 3 — Core v1 retirement alignment

Trans has four call sites still on core v1 HTTP. Core's Phase 4b deletes those routes on **2026-10-31**, so this phase is date-driven from outside and runs in parallel with the rest.

The earlier idea of a trans-side client abstraction with its own shadow was **withdrawn** after reading the core epic: core does the v1 → v2 switch server-side, per function, so callers do not change. Building a second switching layer in trans would duplicate VP-18122–18130 and would collide with the epic's own highest-listed risk, the proto freeze. Concretely that means: **do not touch the vendored core protos in either repo while the reverse proxy is live.**

Measured, so the scope is smaller than it looks: over 27.9 hours, `list-customer-by-id` was called 448 times from trans v1 and 19 from trans v2 — alive. `create-patient`, `create-patient-new` and `login_via_session` were called **zero** times, but both create calls sit on a batch path that may simply not have run in the window, so they need a longer read before being called dead.

### Phase 4 — Infrastructure and resilience

Shipped: real deadlines on the gRPC channels in both services, replacing a 30 s timeout that was never applied and a retry policy that sat beside it doing nothing.

Remaining: CPU requests and memory/CPU limits (neither deployment has limits today), then an HPA; the trans v1 logging interceptor, which `JSON.stringify`s every request and response body — both a CPU cost and a PHI-in-logs path, and already agreed as not a functional change; and aligning the Node versions (v1 on 22, v2 on 20).

### Phase 5 — Pass-through endpoint retirement

Three groups, and only one is removable: routes carrying a PHI ownership gate stay in trans (or the gate moves into the target service first — it may never simply be bypassed); the trans v1 gRPC `TransService` has three internal consumers and is not in scope at all; what is left is pure forwarding with no gate and no aggregation, where the front end can call the target directly. That needs a front-end ticket, a deprecation log first, and 30 days at zero traffic before removal.

`web-homepage-api` was handed over as a merge candidate. After reading it, the recommendation is **not** to merge it: 72 of its routes are the marketing website CMS, backed by Mongo, with no relationship to PHI or to what trans is for. Its only overlap with trans is three report-action endpoints. The recommendation is to fix its delivery pipeline where it stands — it deploys today by `ssh` under a personal account with credentials in the Jenkinsfile — and decide the three endpoints separately.

---

## 5. Proposed timeline for the epic

Dates for Phase 1 are firm enough to commit; later ones are targets that firm up as each phase gets its own doc.

| Milestone | Target | Notes |
|---|---|---|
| Kickoff | 2026-09-10 (done) | Ownership Ray → Yekai |
| Phase 0 — measurement and gate | 2026-09-16 (done) | Ranking, green baselines, CI gate live in both repos |
| Phase 1 detailed doc | 2026-09-18 (done) | This page's child |
| Phase 1 dev complete | **2026-10-02** | ~6 trans-side dev-days; two items gated on other teams |
| Phase 2 next slice (`getSetting`, PNS) | **2026-10-16** | Sized after Phase 1's call-graph cleanup lands |
| Phase 3 — trans off core v1 HTTP | **2026-10-30** | Hard deadline: core deletes the routes 10-31 |
| Phases 4–5 | TBD | Scoped when Phase 2 closes |

---

## 6. Consumer inventory and migration runbook

Two instruments were used, because neither alone is sufficient. **GitHub code search across all 138 repos in the `Vibrant-America` org** finds callers that hard-code a URL, but cannot see a value that lives only in a Kubernetes ConfigMap. **A scan of every ConfigMap in the production cluster** finds those, but cannot see a repo that is not deployed there. Run together on 2026-09-21, they agree, and the result is a closed list.

Code search returned exactly two repos outside the trans services themselves: `LIS-backend-billing` (a hard-coded cloud-proxy URL) and `LIS-setting-consumer` (its own docs and a source comment). Everything else that matched — `LIS-Shipping`, `LIS-backend-results-*`, `LIS-backend-coreSamples`, `LIS-Sample`, `lis-backend-emr-v2`, `LIS-Report` — matched on gRPC *method names* that those services **implement**. They are downstream of the proxy, not callers of it. `Vibrant-knowledge` and `knowledge-graph` are documentation mirrors.

### Who is actually configured to call the proxy

| Consumer | ConfigMaps | Keys pointing at a proxy | Evidence |
|---|---|---|---|
| **LIS-setting-consumer** | `lis-setting-consumer-config`, `-local-config`, `-st-config`, `-local-st-config` | 4 each | **Confirmed by traffic.** In a window where every pod predated the traffic, 100% of `/proxy/grpc/getKitStatus` requests came from its three replicas (`axios/1.4.0`, no `x-forwarded-for`, so in-cluster) |
| **LIS-transformer-v2** | `lis-transv2-config`, `-st` | 4 | Three are stale — the code is mode-gated to `grpc` and reads none of them. `skin_placepatientorders` is still read |
| **LIS-transformer (trans v1 itself)** | `lis-trans-config`, `-st` | 14, all `…/lis/cloud-proxy/…` | 0 code reads. **See the note below — these were reported removed and are present** |
| **LIS-backend-billing** | — (hard-coded in source) | 1 | `ProZOrderServiceImpl.java:115`, addresses the on-prem cloud-proxy |

> **A correction this scan produced.** The Phase 1 page listed trans v1's 14 dead cloud-proxy keys (item S6) as already removed. They are all present in `lis-trans-config` today — and also in `lis-trans-config-st`, which rules out the "removed, then reverted by a `kubectl apply`" explanation, because a staging-first removal would have left staging clean. S6 was never executed; it was recorded as shipped in error, and the Phase 1 page has been corrected. The work itself is unchanged and small: delete 14 keys that no code reads. The lesson is the reason Phase 0 wants ConfigMap drift detection — cluster state is not verifiable from a document, and a claim about it has to be re-read from the cluster.

### Runbook — what each consumer changes, and to what

**LIS-setting-consumer** — the only confirmed live consumer, and the owner of the busiest proxy route. Four keys, in all four ConfigMaps (prod, st, local, local-st — staging first).

| Key | Today | Change to | What must come with it |
|---|---|---|---|
| `proxy_getkit` | `lis-trans-service…:3146/proxy/grpc/getKitStatus?sample_id=` | LIS-Shipping gRPC `getKitStatusBySampleId` | The metadata construction (`createMetadataForCoresampleV2`) and the proto3 normalisation that turns an omitted `packages` into `[]` — omitting the latter is Sentry #68038 |
| `proxy_getresult` | `…/proxy/grpc/getPatientTestsResult?patient_id=` | test-connect gRPC | The same metadata construction |
| `url_downloadTestOrderPDFv2` | `…/proxy/old-report/downloadTestOrderPDF` | **Interim:** same host, path `/trans/downloadTestOrderPDF`. **Target:** lis-order, once it owns the endpoint | Both routes enforce sample ownership, but they differ in identity resolution — the proxy route reads `req.user` only, the `/trans` route uses `resolveIdsForHttpOptional`, which falls back to query arguments when a claim is absent from the JWT. setting-consumer authenticates with a service token whose `user_id` is `0`, so **verify on staging that the trusted-internal bypass resolves the same way on both routes before switching** |
| `skin_placepatientorders` | `…/proxy/grpc/sendSkinPlacePatientOrders` | `crmapi` directly | The payload rewrite (`comments` is set from `julien_barcode`) and the forwarded `Authorization`. **Configured but with no observed traffic in 15 days — confirm it is used at all before migrating; if not, delete the key** |

**LIS-transformer-v2** — two ConfigMaps.

| Key | Today | Change to |
|---|---|---|
| `proxy_getkit`, `proxy_getteststatus`, `proxy_getQuestionaire` | trans v1's proxy routes | **Delete.** The code selects gRPC directly and reads none of them; they are the stale keys Phase 1 item P1-F removes alongside the `TRANS_PROXY_GRPC_MODE` branches |
| `skin_placepatientorders` | trans v1's proxy route | Still read. Follows the same destination as setting-consumer's: `crmapi` directly, carrying the payload rewrite |

**LIS-transformer (trans v1)** — delete all 14 `…/lis/cloud-proxy/…` keys from `lis-trans-config` and `-st`, after confirming the 0-read finding against current `main`. No code change.

**LIS-backend-billing** — replace the hard-coded `…/lis/cloud-proxy/grpc/sendSkinPlacePatientOrders` at `ProZOrderServiceImpl.java:115` with a direct `crmapi` call, carrying the payload rewrite. Needs a ticket on that team; the on-prem cloud-local-proxy cannot be scaled to zero until it lands.

### Sequencing note

Nothing above should move before the route it targets is confirmed. Two of the four setting-consumer keys are ready to plan now; `downloadTestOrderPDF` wants the staging identity check first; `skin_placepatientorders` wants a usage check first. Staging ConfigMaps change before production in every case, and the previous value is recorded in the ticket so a rollback is a single `kubectl edit`.

---

## 7. Open items that need a decision or another team

1. **Branch protection** on `main` in both repos, marking the test job as required. One-time admin action.
2. **On-prem ingress access logs** for `cloud-local-proxy` — needed to finish the retirement and not available from this side.
3. **`LIS-backend-billing`** has the cloud-proxy URL hard-coded; repointing it needs a ticket on that team, and the on-prem proxy cannot be scaled to zero before that lands.
4. **Where the `web-homepage-api` report-action endpoints belong**, and who owns them.
5. **An unidentified in-cluster client** is still calling the trans v1 proxy routes. See the Phase 1 doc — it is instrumentation, not investigation, that will settle it.
6. **VP-18261** (the twin half) is still open. The phase structure above is written to absorb it rather than to pre-empt it.
