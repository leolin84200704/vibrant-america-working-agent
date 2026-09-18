# Jira drafts — 2026-09-18 (not posted; awaiting Leo)

Two drafts: a first comment for VP-18262, and the Timeline rows for epic VP-18260.
Both are written in English per the Jira convention. Neither has been posted.

---

## Draft 1 — comment on VP-18262

> **Investigation complete; plan delivered.**
>
> Both halves of the deliverable are on Confluence:
>
> - [Trans v1 / v2 Optimization — Phased Plan (VP-18260)](https://vibrantamerica.atlassian.net/wiki/spaces/LIS/pages/2697461770) — the phases, what each aims at, and why they run in that order.
> - [Phase 1 Detail — Remove the Detours](https://vibrantamerica.atlassian.net/wiki/spaces/LIS/pages/2696740867) — scope, approach, affected components, risks and sizing, at the level needed to cut tickets. 13 tickets are listed ready to create; ~6 trans-side dev-days, two items gated on other teams.
> - [Shipped Changes & Measured Impact](https://vibrantamerica.atlassian.net/wiki/spaces/LIS/pages/2684321795) — what has already gone out while investigating, and what it measurably did.
>
> **What the investigation found.** 11 endpoints exceed a 2 s p95 with at least 100 hits over 7 days, measured on trace metrics rather than sampled spans. Peak hour is not the cause: peak p95 sits within ±5% of the weekly p95, so the latency is structural. Three structural causes, in cost order: detours (same-cluster services addressed over the public ingress, 0.8–3.8 s per call; trans v2 calling trans v1 over HTTP to reach a gRPC service; a 2023 proxy for a network split that has since been closed), fan-out against core (365 gRPC calls in one request; independent stages run in series), and no safety net — neither repo ran tests or typecheck anywhere in the deploy path.
>
> **Already shipped while investigating**, measured on matched business-hour windows on consecutive weekdays: createPatient p50 3.68 s → 2.08 s (−43%), patientTestResultnewrange p50 2.17 s → 1.76 s, getTimeLine p50 2.14 s → 1.78 s, findPatient p95 2.31 s → 1.88 s, with no movement in error rates. Both deploy pipelines now run typecheck and unit tests, and the unit-test baselines are green in both repos (they were 17/46 and 7/52 red). Profiling also turned up a patient-facing defect: a failed kit lookup was being reported to the timeline as "no report" rather than as a failure — fixed in LIS-transformer #793, and in the 24 hours since it went live it has caught 3 real failures out of 1,512 lookups that would previously have been silent.
>
> **Proposed dates for the epic Timeline:** Phase 1 dev complete 2026-10-02; Phase 2 next slice 2026-10-16; Phase 3 (trans off core v1 HTTP) 2026-10-30, which is a hard date because core deletes those routes on 10-31.
>
> **Two things need someone outside this ticket:** branch protection on `main` in both repos has to mark the test job as a required status check, and the on-prem ingress access logs for `cloud-local-proxy` need Ray. VP-18261 is the other half of this joint deliverable and is still open; the phase structure above is written to absorb it rather than pre-empt it.

---

## Draft 2 — Timeline & milestones rows for epic VP-18260

The epic's Timeline table currently has `—` in every Target and Actual cell below Kickoff.
Proposed replacement rows (Milestone / Target / Actual / Notes):

| Milestone | Target | Actual | Notes |
|---|---|---|---|
| Kickoff | 2026-09-10 | 2026-09-10 | Ownership handoff Ray → Yekai; reference set to VP-17348 |
| Optimization plan (Yekai team) | 2026-09-18 | 2026-09-18 | Phased plan + Phase 1 detail delivered (VP-18262); VP-18261 still open |
| Phase 1 dev complete | 2026-10-02 | — | Routing-layer detours; ~6 trans-side dev-days; 2 items gated on other teams |
| Phase 2 next slice | 2026-10-16 | — | `getSetting` amplifier + PNS resolver fan-out |
| Phase 3 — trans off core v1 HTTP | 2026-10-30 | — | Hard deadline: core deletes the v1 HTTP routes on 10-31 |
| Dev complete | TBD | — | All tickets dev-complete; scoped when Phase 2 closes |
| QA complete | TBD | — | ~3–9 business days |
| GA / launch | TBD | — | |

Note: this changes an epic description that the PM owns, so it is a draft rather than an edit.

---

## Open question for Leo

VP-18261 (Yekai, the twin half) was re-dated to **2026-09-24** on 09-17 and is still Dev To Do.
VP-18262 is still due **2026-09-18**. Should this one move to 09-24 to match, or close on today's
delivery with Yekai's half following separately? Changing the due date is a Jira field edit, so it waits.
