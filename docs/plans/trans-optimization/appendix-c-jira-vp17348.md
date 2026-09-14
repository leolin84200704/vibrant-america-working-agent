# Appendix C — Jira dump: VP-17348 epic + Core v1 REST Retirement tickets (REST API, 2026-09-11)

> Fetched via Jira REST v3 with the agent .env credentials (Atlassian MCP was unavailable to this session). Rendered HTML stripped to text; empty lines are table cells from the epic description.

## VP-17348 — Core Service V1 → V2 Migration
- type: Epic | status: Dev In Progress | priority: P1 - High | assignee: Xiaoye Li | reporter: Xiaoye Li
- created: 2026-07-08T10:39 | updated: 2026-09-11T15:01 | parent: None | labels: []
- links: relates to VP-13757 (Inactive) Transv2 Batch 2

### Description
Goal





Problem
Core V1 must be fully replaced by V2. Approach (2026-07-13 shared-DB pivot; scope revised 2026-07-16; plan v4 2026-07-22): drop the separate Core V2 database — V2 runs directly on V1's database (lis_core_v7), eliminating data sync. In-use components only, re-baselined on 3-day real gRPC traffic (lab-tests excluded); modules regrouped M-A~M-F. Schema drift resolved in V2's ent mapping layer; V1 DB gets lossless-only DDL via Prisma. Sequence: (1) DB unification, (2) V2 code rewrite/refactor, (3) shadow-calls re-enabled as regression acceptance. Staging lessons codified as G7: ent mapping is a global compile-time property — mapping PRs must land atomically with the consumer's DB cutover (shim or same release); CDC pausing uses the dedicated SKIP_V1_SYNC flag (never reuse DRY_RUN); hidden FK dependencies on soon-to-stop mirror tables must be surveyed per module before work starts. Traffic volume is a risk signal, not a scope criterion — zero-traffic in-scope methods still cut over.



Out of scope
Per plan v4 (2026-07-22): serviceship family (serviceship / serviceship_billing_plan / account_subscription / pending_order_credits); international_provider_credential (VI); provider_practice_membership + membership_audit_log; disclaimer_acceptance; delegation; user_metric_preferences / user_unit_preference; test_list_alpha; product_tube_config; customer_address_on_clinics / customer_contact_on_clinics — no mapping, no table moves; if V2 code errors post-cutover, disable/delete the module. patient_variable / vital family: V2-native, stays in the old DB for now, handled separately (hidden FK dependency handled via SKIP_V1_SYNC — see G7). UserService (old M4): no real traffic observed — pending Zhibin's confirmation before formal cancellation. Also: services V1 merely forwards (RBAC pass-through, Audit Log); V1-only tables (59); Role / ReferenceRange / Notification service-layer gaps; V1 infra decommission.









Resources





Type
Link



Shared-DB migration plan v4 (2026-07-22)
Core v1/v2 共库迁移 Plan — Slack canvas



Shadow-call plan (superseded in part)
Core v1 → v2 Shadow-Call task allocation plan (Zhibin Chen) — artifact link



Core v1 REST Retirement plan (v6, 2026-09-03)
344 REST routes → trans + core v2 rpc — artifact link (baseline f217fe40)



Meeting notes
2026-07-06 kickoff; 2026-07-13 shared-DB pivot; 2026-07-16 scope & sequence revision; 2026-07-20 standup; 2026-07-22 plan v4; 2026-08-24 tube direction reversal + shadow rollout cadence; 2026-08-31 read cutover via reverse proxy + REST retirement









Timeline & milestones


Phase 1 — Database unification (V2 cuts over to lis_core_v7, modules M-A~M-F)





Milestone
Target
Actual
Notes



G0 guardrails + global decisions
2026-07-22
2026-07-19
VP-17424; G7 lessons added 07-22



Shadow disconnected + V2 traffic re-baseline
2026-07-22
2026-07-22
3-day real traffic (lab-tests excluded); scope regrouped M-A~M-F (plan v4)



M-B Patient+PNS — staging cutover + validation
—
2026-07-22
Incl. PNS account merge (29,158 aligned) + cross-module column fixes; all known bugs resolved



M-B prod cutover
2026-07-30
2026-07-28
VP-17433 (Zhibin); PNS prod merge ~19k+ accounts / 504 credential drift



M-D InternalUser+RBAC cutover
2026-08-05
2026-07-30
VP-17429 (Zhibin); SSO ties to M-B-validated permission model



M-F Setting+Address/Contact cutover
2026-08-05
2026-08-03
VP-17428, merged w/ 
    
                
            
            VP-17426
        
                                                    Inactive
            
 (Fan Zhou); can run parallel



M-E Customer/Clinic/Sales cutover
2026-08-12
2026-08-10
VP-17434, merged w/ 
    
                
            
            VP-17430
        
                                                    Inactive
            
 (Fan Zhou)



M-C Sample/Order cutover (final)
2026-08-12
2026-08-11
VP-17435 (Zhibin); write-freeze window + order_sync producer closure



M-A Remove Tube Service from core service (Static)
—
—
Called off 2026-08-24 — 
    
                
            
            VP-17436
        
                                                    Done
            
 closed; replaced by VP-17876 + VP-17877 (tube calculation moves into Order Maintain)







Phase 2 — V2 code rewrite / refactor (proto frozen)





Milestone
Target
Actual
Notes



Dead CDC mirror + SkipV1Sync cleanup
2026-08-19
2026-07-30
VP-17507 (Ray); PVS handlers preserved



M-F Setting+Address/Contact refactor (first mover)
2026-08-26
2026-08-17
VP-17513 (Fan Zhou)



M-B Patient / PNS refactor
2026-08-28
2026-08-24
VP-17508 Patient (08-18) / 
    
                
            
            VP-17509
        
                                                    Done
            
 PNS (08-24) — Zhibin; PNS account-merge edge cases in regression



M-D InternalUser+RBAC refactor
2026-08-28
2026-08-24
VP-17510 (Zhibin); OAuth cache clear on deploy



M-E Customer/Clinic/Sales refactor
2026-08-28
2026-08-20
VP-17514 (Fan Zhou)



M-C Sample / Order refactor
2026-08-28
2026-08-28
VP-17511 Sample (Fan Zhou, 08-20) / 
    
                
            
            VP-17512
        
                                                    Done
            
 Order (Zhibin, 08-28); event contracts frozen



Refactor dev complete
2026-08-28
2026-08-28
Gate for Phase 3 shadow re-enable; last in = Order (
    
                
            
            VP-17512
        
                                                    Done
            
)







Phase 3 — Shadow-call regression validation (re-enabled after refactor)





Milestone
Target
Actual
Notes



Shadow infra + all module calls built
2026-07-17
2026-07-17
VP-17349–VP-17358 (Sprint 24)



Shadow calls disabled (framework retained)
—
2026-07-20
~90% of V2 traffic was shadow-generated; Ray's PR + Yekai disconnect



Shadow re-enabled post-refactor (switch on)
2026-08-28
—
Gradual rollout from w/c 08-24, ~2 modules per week (decided 08-24); reuses VP-17349/17353/17355/17358 infra



Per-function diff convergence
rolling
—
Shadow runs per function until it passes; a passing function is then proxied to V2 (Phase 4) while the rest stay under observation. Shadow retires as the last functions cut over (decided 08-31)







Phase 4 — Read cutover via V1→V2 reverse proxy





Milestone
Target
Actual
Notes



Read cutover start
2026-08-31
—
V1 RPC reverse-proxies reads to V2 — callers make no changes (depends on proto freeze). Cutover is per function, driven by shadow results: functions that pass shadow are proxied to V2, the rest keep running under shadow until they pass. Rolling; reversible per function by disabling the proxy



Read cutover complete (all in-scope functions proxied to V2)
end of Sep (target)
—
Shadow framework retires as functions cut over







Phase 4b — Core v1 REST Retirement (344 HTTP routes → trans + core v2 rpc)


Separate track from the gRPC reverse proxy above: 344 core v1 REST routes, only 19 with 30d traffic (90% from the retiring old order). Strips the billing hop rather than re-protocoling it. Front-end batch rides rebranding; rebranding release takes priority — an endpoint not ready when rebranding touches it drops off and goes independent, blocking no one. Doc v6 (Ray approved 09-03). All tickets in Team Ray Sprint 28.





Milestone
Target
Actual
Notes



P0 log probe + dashboard
2026-09-11
—
VP-18140 (interceptor, Zhibin) + 
    
                
            
            VP-18141
        
                                                    Dev Complete
            
 (dashboard, Fan); source of truth for all deletions; observe one monthly cycle



P1 fill v2 gaps
2026-09-15
—
VP-18142 write-back (Zhibin, largest build) / 
    
                
            
            VP-18143
        
                                                    Dev Complete
            
 multi_login_test (Fan) / 
    
                
            
            VP-18144
        
                                                    Dev In Progress
            
 shadow 7 zero-traffic rpc (Fan)



P2-A ride rebranding (FE)
2026-09-15+
—
VP-18145 getJwtTokenCustomerList (coord 
    
                
            
            VP-17399
        
                                                    QA Review
            
) / 
    
                
            
            VP-18146
        
                                                    Dev Complete
            
 multiLogin (coord Jiafan VP-17783~17792/17800); FE unassigned; rebranding site only



P2-B delete dead code
2026-09-15
—
VP-18147 (Fan); independent



P2-C new order backend ownership
2026-09-11
—
VP-18148 (Ray, self-claimed); C1–C4 split after Fangyuan confirms; parity required



P3 residual callers → v2
2026-09-30
—
VP-18149 order-management pilot / 18150 LIS-Shipping / 18151 LIS-Sample / 18152 trans / 18153 portal policy (FE) / 18154 lis_log_in (FE) / 18155 questionnaire callers



P4 delete HTTP surface
2026-10-31
—
VP-18156 (Zhibin, 4 batches); per-method not class-level (
    
                
            
            VP-17320
        
                                                    Done
            
); gated on P0 probe



P5 close HTTP ingress
2026-11-15
—
VP-18157 (Fan); staging then prod; reopen VP-17276







Phase 5 — Write migration





Milestone
Target
Actual
Notes



Dev start
2026-09-11
—
Per-service write migration to V2 APIs; simplified by shared DB; scope not yet broken into tickets



Dev complete
2026-09-25
—
Runs in parallel with Phase 4







Phase 6 — V1 deprecation





Milestone
Target
Actual
Notes



GA / launch
2026-09-28
—
V1 decommission-ready; coresamplesv2 DB retired. Prerequisite: reverse proxy removed — while reads are proxied through V1, V1 cannot be retired









Risks & dependencies



	- [High] G3 A/B direction on M2M mapping tables — reversed pair silently corrupts relation data. Manual verification + read/write round-trip tests per pair.

	- [High] G7 atomic alignment — ent mapping is global compile-time; a mapping PR landing before its consumer's cutover breaks not-yet-cut services (valogin 401 incident on staging). Shim the old DB or ship mapping + client cutover in one release.

	- [High] G0 — ent migrate against V1 DB = incident. Guardrails in 
    
                
            
            VP-17424
        
                                                    Done
            
.

	- [High] order_info.patient_id dead column (M-C) — decision still open: backfill + restore dual-write vs V2 M2M edge mapping.

	- [High] Proto freeze is now a long-lived hard dependency, not just a validation-period discipline — the V1→V2 reverse proxy (Phase 4) only works while V1 and V2 signatures stay identical. No proto/event-contract divergence is permitted for as long as the proxy is in place.

	- [Medium] Reverse proxy makes V1 a permanent hop on the read path until it is removed — added latency and an extra failure surface on V1, and V1 decommission (Phase 6) is blocked until the proxy is retired. V1 is no longer “winding down”; its stability stays load-bearing.

	- [Medium] Residual V1 REST APIs — 344 core v1 HTTP routes now scoped and ticketed as Phase 4b (P0–P5, VP-18140~18157); deletions gated on the P0 log probe ("zero traffic" ≠ "unused"). P2-C (payment/PHI back-office logic) must hold end-to-end parity; front-end batch must not block the rebranding release.

	- [Medium] Hidden FK dependencies on mirror tables — non-migrating V2-native features may FK-depend on mirrors being stopped (patient_variable_events → v2 patient case); survey per module before stopping CDC.

	- [Medium] Never reuse DRY_RUN to stop CDC — it already controls two dormant prod mechanisms; use dedicated SKIP_V1_SYNC (consumer keeps listening/acking, skips v1→v2 upserts only).

	- [Medium] Traffic-evidence shelf life — 30-day snapshots were contaminated by non-real callers (shadow, lab-tests); re-calibrate scope with fresh real traffic before each cutover.

	- [Medium] In-production data moves need write-freeze windows: order_revenue, transactions, test_list, critical_readout_authorized_contact, sales_*.

	- [Medium] V2 Kafka consumers write V1 production tables directly post-cutover (G5) — review to prod-DB standards; row-count-anomaly tables (tube_receive, contact) need pipelines confirmed stopped before discard.

	- [Medium] OAuth Redis cache (M-D): clear internal_user_role_* (TTL 10h) at cutover. G1 timestamp/timezone spot checks per module. Role / ReferenceRange / Notification service gaps remain.






Notes & decisions



	- 2026-08-31 — Meeting
	
		- Read cutover via reverse proxy. Phase 4 is done by reverse-proxying V1 RPC to V2 — callers make no changes (relies on proto freeze). Cutover is per function, driven by shadow results: when e.g. 20 of a service's functions pass shadow comparison, those 20 are proxied to V2 while the rest stay under shadow observation until they pass, then get replaced. Rolling. Overall read cutover targeted to finish end of September. Shadow calls retire as functions cut over.

		- Residual V1 APIs. Discovered that some Core V1 APIs still remain and need handling (not covered by the reverse proxy / module cutovers). Zhibin to provide a doc listing these APIs and the disposition for each. → Doc delivered 09-03 (v6, Ray approved): 344 REST routes, ticketed as Phase 4b (VP-18140~18157). Front-end batch rides rebranding (rebranding site only); rebranding release takes priority. Old order back-office logic goes to new order backend (Fangyuan, Ray owns the handoff 
    
                
            
            VP-18148
        
                                                    Dev To Do
            
).

		- Phase 5 (write migration) — unchanged for now.

	
	

	- 2026-08-24 — Meeting
	
		- Tube direction reversed. Removing the tube service from core service is called off. Static tube calculation moves into Order Maintain, at orderable item level, rewritten directly. Ray to produce a list of every orderable item's tube(s) and their combinations with the corresponding tube, for lab review; lab sign-off gates the rewrite. VP-17436 closed, replaced by VP-17876 (mapping list, 08-28) and VP-17877 (rewrite, 09-11).

		- Shadow calls rolled out gradually. Starting this week, approximately two modules per week, rather than switching all modules on at once.

	
	

	- 2026-08-18 — Timeline accelerated: all remaining refactor tickets pulled to 08-28 (was 09-02~09-11), shadow-call switch-on same day, ~1 week observation + adjustments → refactor/validation complete 09-11, then read + write cutover in parallel to dev complete 09-25, GA 09-28. Phase 1 Actual dates backfilled from child-ticket completion: G0 07-19, M-B prod 07-28, M-D 07-30, M-F 08-03, M-E 08-10, M-C 08-11 — every module landed early. M-A (
    
                
            
            VP-17436
        
                                                    Done
            
, Ray) is the only Phase 1 item still open, retargeted 08-28 and now also carries shadow re-enable. Phase 2: 
    
                
            
            VP-17507
        
                                                    Done
            
 CDC cleanup done 07-30 (moved to Ray, scope smaller than estimated), 
    
                
            
            VP-17513
        
                                                    Done
            
 M-F refactor done 08-17.

	- 2026-07-27 — Phase 2 (V2 rewrite/refactor) tickets created: 
    
                
            
            VP-17507
        
                                                    Done
            
 (dead CDC mirror + SkipV1Sync cleanup, PVS handlers preserved) + module rewrites 
    
                
            
            VP-17508
        
                                                    Done
            
 Patient / 
    
                
            
            VP-17509
        
                                                    Done
            
 PNS / 
    
                
            
            VP-17510
        
                                                    Done
            
 InternalUser+RBAC / 
    
                
            
            VP-17512
        
                                                    Done
            
 Order (Zhibin) and 
    
                
            
            VP-17511
        
                                                    Done
            
 Sample / 
    
                
            
            VP-17513
        
                                                    Done
            
 Setting+Address/Contact / 
    
                
            
            VP-17514
        
                                                    Done
            
 Customer/Clinic/Sales (Fan Zhou). Ownership mirrors Phase 1; Sample rewrite moved to Fan Zhou for load balance. Hard constraint on all: proto/event-contract freeze. Ray's tube-service dead-code cleanup stays inside Phase 1 
    
                
            
            VP-17436
        
                                                    Done
            
. Dependencies: each rewrite blocked by its Phase 1 cutover ticket + 
    
                
            
            VP-17507
        
                                                    Done
            
.

	- 2026-07-22 — Plan v4: traffic re-baselined (3-day real gRPC, lab-tests excluded); modules regrouped M-A~M-F; exclusion list confirmed (serviceship, VI credential, memberships, delegation, preferences, etc.); UserService (old M4) pending Zhibin confirmation. M-B Patient+PNS completed and validated on staging: PNS account merge (29,158 aligned; prod ~19k+ pending), cross-module column fixes (order_info +2, address, sample, tube, tube_type, internal_user), beta_programs mapping, _clinictocustomer M2M fixed. New G7 lessons: mapping-PR/consumer atomic alignment (valogin 401), dedicated SKIP_V1_SYNC flag, hidden FK survey (PVS case), traffic-evidence shelf life. Tickets restructured: VP-17425/17426/17430 cancelled (merged into M-A/M-F/M-E), 
    
                
            
            VP-17436
        
                                                    Done
            
 → Ray, 
    
                
            
            VP-17427
        
                                                    Done
            
 → backlog pending confirmation.

	- 2026-07-20 — Standup: Zhibin on M-B Patient DB cutover; tube service to Ray; Yekai disconnecting shadow calls; traffic re-pull planned Wed.

	- 2026-07-16 — Scope narrowed to in-use components (VI excluded). Sequence: DB unification → V2 rewrite/refactor → shadow-call regression. Ray found V2 traffic stats ~90% shadow-generated; PR merged disabling shadow (framework retained).

	- 2026-07-13 — Plan pivot: drop separate Core V2 DB; V2 runs on lis_core_v7. Data sync eliminated; drift fixed in V2 ent mapping; V1 lossless-only DDL via Prisma; CDC deprecated with V1 as source of truth.

	- 2026-07-08 — Shadow-call tickets VP-17349–VP-17358 created (Sprint 24, done 07-17). Shared-DB tickets VP-17424–VP-17436 created 07-16 (Sprint 25).

	- 2026-07-06 — Kickoff. Top blockers: data sync, write-op complexity, cutover testing. Initial decision: read/write separation with offline sync detection. (Superseded by 07-13 shared-DB pivot.)

## VP-18152 — [Core v1 REST Retirement][P3] trans v1/v2 → unified gRPC path to core v2
- type: Task | status: Dev To Do | priority: P2 - Medium | assignee: Zhibin Chen | reporter: Xiaoye Li
- created: 2026-09-04T15:34 | updated: 2026-09-10T10:13 | parent: VP-17348 | labels: []
- links: is tested by QH-7030 (To Do) [Core v1 REST Retirement][P3] trans v1/v2 → unified gRPC path to core v2

### Description
Part of Core v1 REST Retirement (doc baseline f217fe40, v6), under VP-17348. Depends on P0 (VP-18140) + P1-1 (VP-18142).


Scope



	- Consolidate trans v1/v2 onto the gRPC path already in use for core v2 (stop reaching core over v1 HTTP).




Acceptance criteria



	- trans no longer reaches core over v1 HTTP.

## VP-18140 — [Core v1 REST Retirement][P0] Global HTTP interceptor — structured request logging
- type: Task | status: Dev Complete | priority: P2 - Medium | assignee: Zhibin Chen | reporter: Xiaoye Li
- created: 2026-09-04T15:31 | updated: 2026-09-10T13:09 | parent: VP-17348 | labels: []
- links: is tested by QH-7018 (To Do) [Core v1 REST Retirement][P0] Global HTTP interceptor — structured request logging

### Description
Part of Core v1 REST Retirement (doc baseline f217fe40, v6, Ray approved 2026-09-03), under VP-17348. Before deleting any route we need real evidence of who calls what.


Scope



	- Add a global interceptor on core v1 that logs every HTTP request: route, User-Agent, X-Forwarded-For, JWT present/absent, service-name. Structured log to Datadog.




Why



	- "Zero traffic" is not "unused"; APM only covers tracer-instrumented clients and only 30d. This probe is the source of truth for all Phase 4 deletions; must run a full monthly cycle to catch month-end / quarterly batch jobs.




Acceptance criteria



	- Every core v1 HTTP request emits a structured log line; fields queryable in Datadog.




Companion: P0-2 dashboard (VP-18141, Fan).

### Comment — Zhibin Chen 2026-09-10T13:09
Dev complete — shipped to staging and prod on 2026-09-10.


Implementation


Global Express middleware (src/http-request-log.middleware.ts), registered in main.ts after cookieParser. Emits one structured winston JSON line per HTTP request on res "finish".


Implemented as middleware rather than a Nest interceptor on purpose: interceptors run after guards and only for matched routes, so guard rejections (401) and unmatched paths (404) would never be logged — and those are exactly the callers we need evidence of. Middleware also gives us final status code and latency. No sampling.


Fields (all queryable in Datadog)


event (= core_v1_http_request), method, route (Express route template, e.g. /api/customer/:id; unmatched paths are unmatched), path, status, duration_ms, api_version, user_agent, x_forwarded_for (first hop), remote_ip, jwt_present, jwt_source (header/cookie/none), jwt_sub, jwt_role, service_name, environment, server_type, version.


JWT is decoded but NOT verified (verification stays the guards' job); only sub and role are recorded, never the token. Skips /api/Health and /api/doc.


PRs



	- main: #1753 (merged, c18a4371)

	- staging: #1752 + follow-up #1754 (merged)




Verification



	- 20 unit tests, tsc clean.

	- Staging (lis-core-staging): probed 200 / 401 / 404 / skip paths, all correct, 0 errors.

	- Prod (lis-core-deploymentv7 5/5, lis-core-kafka 2/2): ~497 events in the first 10 minutes. Early traffic picture — Java/1.8.0_202 Bearer callers hitting get-patient-by-id, find-customer, list-customer-by-id/:clinic_id; plus vibrant/order-service-spring and an axios client.

	- Datadog query: @event:core_v1_http_request




Two notes for the dashboard (
    
                
            
            VP-18141
        
                                                    Dev Complete
            
) and QA (
    
                
            
            QH-7018
        
                                                    To Do
            
)



	- Filter tiers by @environment:Prod / @environment:Staging. Do NOT use the env or service tags — both tiers report env:prod and service:lis-core-deploymentv7, because winston defaultMeta in src/logger.ts hardcodes the service name and overrides the injected Datadog tags. Pre-existing behaviour, not introduced here.

	- custom.* attributes need facets created in Datadog before they can be used in dashboard group-bys.




Also worth flagging for Phase 4: every HTTP caller observed so far sends no service-name header, so service_name is unknown across the board. Caller attribution will have to come from user_agent + jwt_sub.

### Comment — Automation for Jira 2026-09-10T13:09
👋 Hi Xiaoye Li,


This ticket is now in *Dev Complete*.

Please proceed to the next stage, or move it directly to *Done* if everything looks good.


Thanks!

## VP-18141 — [Core v1 REST Retirement][P0] Dashboard — v1 HTTP vs v2 rpc dual curve
- type: Task | status: Dev Complete | priority: P2 - Medium | assignee: Fan Zhou | reporter: Xiaoye Li
- created: 2026-09-04T15:31 | updated: 2026-09-10T09:41 | parent: VP-17348 | labels: []
- links: is tested by QH-7019 (To Do) [Core v1 REST Retirement][P0] Dashboard — v1 HTTP vs v2 rpc dual curve

### Description
Part of Core v1 REST Retirement (doc baseline f217fe40, v6), under VP-17348. Companion to P0-1 (VP-18140).


Scope



	- Datadog dashboard plotting core v1 HTTP volume and the corresponding core v2 rpc volume as two curves per endpoint. Migration progress reads as one curve down, the other up.




Acceptance criteria



	- Dashboard live for the 9 active endpoints; observe one full monthly cycle before any deletion.

### Comment — Automation for Jira 2026-09-10T09:41
👋 Hi Xiaoye Li,


This ticket is now in *Dev Complete*.

Please proceed to the next stage, or move it directly to *Done* if everything looks good.


Thanks!

## VP-18144 — [Core v1 REST Retirement][P1] Shadow the 7 zero-traffic v2 rpc
- type: Task | status: Dev In Progress | priority: P2 - Medium | assignee: Fan Zhou | reporter: Xiaoye Li
- created: 2026-09-04T15:32 | updated: 2026-09-09T13:18 | parent: VP-17348 | labels: []
- links: is tested by QH-7022 (To Do) [Core v1 REST Retirement][P1] Shadow the 7 zero-traffic v2 rpc

### Description
Part of Core v1 REST Retirement (doc baseline f217fe40, v6), under VP-17348. 7 v2 rpc have proto + Go handler but zero production traffic — "implemented" is not "production-ready". Shadow is a hard prerequisite before cutover.


Endpoints (🟡)



	- ListClinicCustomersByClinicID, CheckPatientsClinic, ListUserPolicyAcceptances, LISLogin, RecordUserPolicyAcceptance, and the remaining 🟡 from the doc's active-endpoint table.




Scope limit (important)



	- This only answers "is the v2 rpc itself correct". It does NOT cover end-to-end response parity — core shadow compares v1 rpc vs v2 rpc, not the FE-visible JSON. Serves the P2-C backend callers.




Acceptance criteria



	- Each of the 7 rpc runs a shadow pass; diffs triaged and resolved.

## VP-18142 — [Core v1 REST Retirement][P1] v2: add UpdatePatientInformantWithWriteBack (proto + handler + write-back)
- type: Task | status: Dev To Do | priority: P2 - Medium | assignee: Zhibin Chen | reporter: Xiaoye Li
- created: 2026-09-04T15:31 | updated: 2026-09-10T10:13 | parent: VP-17348 | labels: []
- links: is tested by QH-7020 (To Do) [Core v1 REST Retirement][P1] v2: add UpdatePatientInformantWithWriteBack (proto + handler + write-back)

### Description
Part of Core v1 REST Retirement (doc baseline f217fe40, v6), under VP-17348. Largest new build; pure dev, can start immediately — v2 currently has NO patient write-back at all.


Scope



	- Add proto + Go handler + write-back logic for PUT /patient/update-patient-with-write-back, mapped to the v2 coresamples_service equivalent.




Beneficiaries



	- LIS-Shipping / LIS-Sample / order-management (3 callers waiting). The billing copy is retiring on its own via patient_cu_trans GA, so billing is not a beneficiary.




Note



	- proto package changes lis.* to coresamples_service.*; downstream stubs regenerate.




Acceptance criteria



	- v2 write-back returns parity with v1; the 3 waiting callers can migrate.




Unblocks P3-1 / P3-2 / P3-3.

## VP-18156 — [Core v1 REST Retirement][P4] Delete core v1 HTTP surface (4 batches)
- type: Task | status: Dev To Do | priority: P2 - Medium | assignee: Zhibin Chen | reporter: Xiaoye Li
- created: 2026-09-04T15:34 | updated: 2026-09-10T10:13 | parent: VP-17348 | labels: []
- links: is tested by QH-7034 (To Do) [Core v1 REST Retirement][P4] Delete core v1 HTTP surface (4 batches)

### Description
Part of Core v1 REST Retirement (doc baseline f217fe40, v6), under VP-17348. Depends on P1 + P2 + P3. Removes the 325 zero-traffic routes plus the migrated active ones, in 4 batches (subtasks under this ticket).


Disposition classes (from doc)



	- A: has traffic, v1 has twin (8) — upstream moved to v2, then delete HTTP

	- B: has traffic, no gRPC (10) — add v2 rpc or move to trans, then delete

	- B2: zero traffic, code still referenced (6) — delete dead caller first

	- C: zero traffic, v1 has twin (86) — delete outright

	- D: zero traffic, ops/debug (97) — fix-* / force-* / test / backfill

	- E: zero traffic, business semantics (135) — go controller-by-controller

	- KEEP: 2 HealthCheck




Method



	- One PR per batch, v1 + v2 lockstep. Delete decorators + HTTP handlers only, do not touch the service layer (gRPC handlers reuse it).

	- Delete per-method, never class-level — on mixed HTTP+gRPC controllers a class-level guard reading switchToHttp() breaks the external gRPC (
    
                
            
            VP-17320
        
                                                    Done
            
 incident).




Gate



	- Every deletion must be justified by the P0 log probe (VP-18140), not the doc table alone.




Acceptance criteria



	- 4 batches merged; core v1 HTTP surface reduced to HealthCheck only.

## VP-18157 — [Core v1 REST Retirement][P5] Close core v1 HTTP ingress
- type: Task | status: Dev To Do | priority: P2 - Medium | assignee: Fan Zhou | reporter: Xiaoye Li
- created: 2026-09-04T15:35 | updated: 2026-09-10T10:25 | parent: VP-17348 | labels: []
- links: is tested by QH-7035 (To Do) [Core v1 REST Retirement][P5] Close core v1 HTTP ingress

### Description
Part of Core v1 REST Retirement (doc baseline f217fe40, v6), under VP-17348. Depends on P4 (VP-18156).


Scope



	- Narrow / remove the wildcard route /v1/lis/lis-core-service(/|$)(.*). The YAML lives in another repo — needs coordination.

	- Staging first, observe two weeks before prod.

	- Reopen VP-17276 — this time it can actually be closed.




Acceptance criteria



	- Ingress closed on staging then prod; 
    
                
            
            VP-17276
        
                                                    Inactive
            
 resolved.

## VP-18149 — [Core v1 REST Retirement][P3] order-management → core v2 gRPC (sample/pilot)
- type: Task | status: Inactive | priority: P2 - Medium | assignee: Zhibin Chen | reporter: Xiaoye Li
- created: 2026-09-04T15:33 | updated: 2026-09-10T10:11 | parent: VP-17348 | labels: []
- links: is tested by QH-7027 (To Do) [Core v1 REST Retirement][P3] order-management → core v2 gRPC (sample/pilot)

### Description
Part of Core v1 REST Retirement (doc baseline f217fe40, v6), under VP-17348. Depends on P0 (VP-18140) + P1-1 (VP-18142).


order-management is a Go repo with an existing core gRPC client — lowest cost, do it first as the template for the other P3 repos.


Scope



	- Switch its core v1 HTTP calls to core v2 gRPC (trans + core v2 where applicable).




Acceptance criteria



	- order-management off core v1 HTTP; pattern documented for P3-2 through P3-7.

## VP-18143 — [Core v1 REST Retirement][P1] Decide multi_login_test ownership + move auth into trans
- type: Task | status: Dev Complete | priority: P2 - Medium | assignee: Fan Zhou | reporter: Xiaoye Li
- created: 2026-09-04T15:32 | updated: 2026-09-11T11:32 | parent: VP-17348 | labels: []
- links: is tested by QH-7021 (To Do) [Core v1 REST Retirement][P1] Decide multi_login_test ownership + move auth into trans

### Description
Part of Core v1 REST Retirement (doc baseline f217fe40, v6), under VP-17348.


POST /user/multi_login_test — no guard, no v1/v2 rpc, zero traffic decay (billing LoginController.java:48 is the only caller, ~50-75/day steady). Likely the last endpoint blocking ingress shutdown, so priority is pulled forward.


Scope



	- It is "swap A's token for B customer's token" = impersonation, so auth belongs in trans. Decide ownership and land the trans-side implementation/target.




Acceptance criteria



	- Replacement path defined and owned; the billing caller has a concrete target.




Unblocks P2-A4 (front-end multiLogin switch).

### Comment — Automation for Jira 2026-09-11T11:32
👋 Hi Xiaoye Li,


This ticket is now in *Dev Complete*.

Please proceed to the next stage, or move it directly to *Done* if everything looks good.


Thanks!

## Children of VP-17348
| key | status | assignee | summary |
|---|---|---|---|
| VP-17349 | Done | Zhibin Chen | [Core Shadow] Template - shadow-call + shared infra |
| VP-17350 | Done | Fan Zhou | Old - [Core Shadow] Sample module shadow-call (19 methods) |
| VP-17351 | Dev Complete | Fan Zhou | [Core Shadow] Customer module shadow-call (13 methods) |
| VP-17352 | Dev Complete | Fan Zhou | [Core Shadow] Clinic module shadow-call (8 methods) |
| VP-17353 | Dev In Progress | Zhibin Chen | [Core Shadow] Setting module shadow-call (5 methods) |
| VP-17354 | Inactive | Fan Zhou | [Core Shadow] Test module shadow-call (2 methods) |
| VP-17355 | Dev In Progress | Zhibin Chen | [Core Shadow] User module shadow-call (5 methods) |
| VP-17356 | Dev Complete | Fan Zhou | [Core Shadow] Internal User module shadow-call (2 methods) |
| VP-17357 | Dev Complete | Fan Zhou | [Core Shadow] Address + Contact + International Credential shadow-call (5 methods) |
| VP-17358 | Dev In Progress | Zhibin Chen | [Core Shadow] Order module shadow-call (2 methods) |
| VP-17424 | Done | Fan Zhou | [Core Shared-DB] G0 guardrails: forbid ent migration against V1 DB + decision meeting prep |
| VP-17425 | Inactive | Zhibin Chen | [Core Shared-DB] M8 Test module cutover to lis_core_v7 (first batch, runbook template) |
| VP-17426 | Inactive | Fan Zhou | [Core Shared-DB] M10 Address/Contact module cutover to lis_core_v7 (first batch) |
| VP-17427 | Done | Zhibin Chen | [Core Shared-DB] M4 User module cutover to lis_core_v7 |
| VP-17428 | Done | Fan Zhou | [Core Shared-DB] M-F Setting + Address/Contact cutover to lis_core_v7 (merged VP-17426) |
| VP-17429 | Done | Zhibin Chen | [Core Shared-DB] M-D InternalUser + RBAC cutover to lis_core_v7 (SSO pitfall) |
| VP-17430 | Inactive | Fan Zhou | [Core Shared-DB] M6 Clinic module cutover to lis_core_v7 |
| VP-17433 | Done | Zhibin Chen | [Core Shared-DB] M-B Patient + PNS cutover to lis_core_v7  |
| VP-17434 | Done | Fan Zhou | [Core Shared-DB] M-E Customer/Clinic/Sales cutover to lis_core_v7 (merged VP-17430) |
| VP-17435 | Done | Zhibin Chen | [Core Shared-DB] M-C Sample/Order cutover to lis_core_v7 (final batch, highest risk) |
| VP-17436 | Done | Rui Chen | [Core Shared-DB & Shadow Call] M-A Remove Tube Service from core service (static implementation) |
| VP-17437 | Done | Zhibin Chen | [Core Shadow] Patient module shadow-call + shared infra |
| VP-17439 | Dev Complete | Fan Zhou | [Core Shadow] Sample module shadow-call (19 methods) |
| VP-17507 | Done | Rui Chen | [Core V2 Refactor] Remove dead CDC mirror consumers + SkipV1Sync branches (preserve PVS) |
| VP-17508 | Done | Zhibin Chen | [Core V2 Refactor] M-B Patient module rewrite (proto frozen) |
| VP-17509 | Done | Zhibin Chen | [Core V2 Refactor] M-B PNS (patient portal) flows rewrite (proto frozen) |
| VP-17510 | Done | Zhibin Chen | [Core V2 Refactor] M-D InternalUser + RBAC module rewrite (proto frozen) |
| VP-17511 | Done | Fan Zhou | [Core V2 Refactor] M-C Sample module rewrite (proto frozen) |
| VP-17512 | Done | Zhibin Chen | [Core V2 Refactor] M-C Order module rewrite (event contracts frozen) |
| VP-17513 | Done | Fan Zhou | [Core V2 Refactor] M-F Setting + Address/Contact module rewrite (proto frozen, first mover) |
| VP-17514 | Done | Fan Zhou | [Core V2 Refactor] M-E Customer/Clinic/Sales module rewrite (proto frozen) |
| VP-17876 | Dev Complete | Zhibin Chen | [Order] Orderable item level tube mapping list for lab review |
| VP-17877 | Done | Rui Chen | [Order] Rewrite static tube calculation at orderable item level in Order Maintain |
| VP-18122 | Dev To Do | Zhibin Chen | [Core V2 Read Cutover] Patient — proxy reads to V2 |
| VP-18123 | Dev To Do | Zhibin Chen | [Core V2 Read Cutover] Setting — proxy reads to V2 |
| VP-18124 | Dev To Do | Zhibin Chen | [Core V2 Read Cutover] User — proxy reads to V2 |
| VP-18125 | Dev To Do | Zhibin Chen | [Core V2 Read Cutover] Order — proxy reads to V2 |
| VP-18126 | Dev To Do | Fan Zhou | [Core V2 Read Cutover] Customer — proxy reads to V2 |
| VP-18127 | Dev To Do | Fan Zhou | [Core V2 Read Cutover] Clinic — proxy reads to V2 |
| VP-18128 | Dev To Do | Fan Zhou | [Core V2 Read Cutover] Internal User — proxy reads to V2 |
| VP-18129 | Dev To Do | Fan Zhou | [Core V2 Read Cutover] Address + Contact — proxy reads to V2 |
| VP-18130 | Dev To Do | Fan Zhou | [Core V2 Read Cutover] Sample — proxy reads to V2 |
| VP-18140 | Dev Complete | Zhibin Chen | [Core v1 REST Retirement][P0] Global HTTP interceptor — structured request logging |
| VP-18141 | Dev Complete | Fan Zhou | [Core v1 REST Retirement][P0] Dashboard — v1 HTTP vs v2 rpc dual curve |
| VP-18142 | Dev To Do | Zhibin Chen | [Core v1 REST Retirement][P1] v2: add UpdatePatientInformantWithWriteBack (proto + handler + write-back) |
| VP-18143 | Dev Complete | Fan Zhou | [Core v1 REST Retirement][P1] Decide multi_login_test ownership + move auth into trans |
| VP-18144 | Dev In Progress | Fan Zhou | [Core v1 REST Retirement][P1] Shadow the 7 zero-traffic v2 rpc |
| VP-18145 | Dev To Do | Zhiheng Wu | [Core v1 REST Retirement][P2-A][FE] Replace getJwtTokenCustomerList (portal home updates tab & whole system) |
| VP-18146 | Dev Complete | Zhiheng Wu | [Core v1 REST Retirement][P2-A][FE] Switch multiLogin front-end call |
| VP-18147 | Dev In Progress | Fan Zhou | [Core v1 REST Retirement][P2-B] Delete billing dead code (3 endpoints) |
| VP-18148 | Dev To Do | Rui Chen | [Core v1 REST Retirement][P2-C] Confirm new order backend ownership — no core v1 HTTP |
| VP-18149 | Inactive | Zhibin Chen | [Core v1 REST Retirement][P3] order-management → core v2 gRPC (sample/pilot) |
| VP-18150 | Dev To Do | Fan Zhou | [Core v1 REST Retirement][P3] LIS-Shipping → core v2 (update-patient-with-write-back caller) |
| VP-18151 | Dev To Do | Zhibin Chen | [Core v1 REST Retirement][P3] LIS-Sample → core v2 |
| VP-18152 | Dev To Do | Zhibin Chen | [Core v1 REST Retirement][P3] trans v1/v2 → unified gRPC path to core v2 |
| VP-18153 | Dev To Do | Zhiheng Wu | [Core v1 REST Retirement][P3][FE] va-portal policy endpoints (2) → core v2 |
| VP-18154 | Dev To Do | Zhiheng Wu | [Core v1 REST Retirement][P3][FE] LIS-frontend lis_log_in → core v2 |
| VP-18155 | Dev To Do | Fan Zhou | [Core v1 REST Retirement][P3] Self-owned callers of getQuestionnaireRequiredMap → core v2 |
| VP-18156 | Dev To Do | Zhibin Chen | [Core v1 REST Retirement][P4] Delete core v1 HTTP surface (4 batches) |
| VP-18157 | Dev To Do | Fan Zhou | [Core v1 REST Retirement][P5] Close core v1 HTTP ingress |
| VP-18192 | Dev To Do | Zhibin Chen | [Core V2] OrderService.GetOrder drops order_flags[].order_flag_allow_duplicates_under_same_category (ent Bool → proto string via util.Swap) |
| VP-18193 | Dev To Do | Zhibin Chen | [Core V2] OrderService.GetOrder returns one empty samples element for sample-less orders; v1 returns [] |
| VP-18216 | Dev Complete | Fan Zhou | [Core v1 REST Retirement][P2-A][BE] Wrapper for getJwtTokenCustomerList replacement |
| VP-18237 | Dev Complete | Zhibin Chen | [Core V2] Cancel-order event is silently dropped when the sample row does not exist yet |