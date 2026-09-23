# VP-18320 — Jira comment draft (widening + re-measured evidence)

**Status:** DRAFT — not posted. Awaiting Leo's go-ahead.
**Target:** VP-18320, as a comment. Also update the ticket description's Scope section to match.
**Written:** 2026-09-23

---

## Comment body

**Widening this ticket to include the ten unused `/proxy/old-report/*` routes.** Proposed in my
comment of 2026-09-21, no objection since, so they now ride the same announcement and the same
removal date. `downloadTestOrderPDF` is not among them — it takes about 1,380 requests a day and
is being handled separately.

**Removal list — 13 routes.**

`/proxy/grpc/`: `getTestStatus`, `getQuestionaireBySampleId`, `listTnpCode`.

`/proxy/old-report/`: `getRequisitionForm`, `GenerateBatchReqOrReportV2`,
`GenerateOnlineZipDownloadV2`, `getOrderSummaryReportZip`, `GetSpecificReports`,
`GenerateOnlineSummaryReport`, `GenerateProducctSummaryReport`, `GenerateProducctReport`,
`checkIfPersonalizedReportCanBeCreated`, `oneClickPersonalizedReport`.

**Every one of the ten has a replacement that exists today: the same-named route under
`/trans/*`, in this same service.** They are not a parallel implementation — eight of the
`/trans` twins call `TransService`, which delegates into the very same `OldReportProxyService`
methods the proxy handlers call, and the other two call that service directly. Same downstream,
same document, same environment keys. What the `/trans` path adds is a navigator permission
gate, Kafka audit events and language resolution, so the copy being removed is the less audited
of the two.

Two of the ten are not drop-in replacements, and it is better to say so now than to have someone
find out:

- `GetSpecificReports` — the proxy copy streams the raw `.gz`; the `/trans` twin unzips it and
  returns JSON. A caller moving across stops unzipping.
- `getOrderSummaryReportZip` — the proxy copy scopes the downstream fetch by the
  `customer_id_arr` query parameter; the `/trans` twin scopes it by the caller's JWT. Same
  artefact, stricter scoping.

**Evidence, re-measured today** over the full 15 days of request logs we retain, 2026-09-08 to
2026-09-23. Counted from request logs rather than APM spans — spans are sampled at roughly 0.4%
and understate sparse traffic by two orders of magnitude.

- `getTestStatus` and `getQuestionaireBySampleId` ran 129–1,876 times a day before the
  2026-09-16 cutover, tracking each other to within one call on every single day, with
  `getKitStatus` at exactly twice their rate. That is one caller's fixed per-sample pattern —
  trans v2's `patientProfile` — not a population of callers; a second independent consumer would
  break the lockstep on the days it ran, and it never breaks. Both have been at **exactly zero
  for seven consecutive days** since that caller moved to direct gRPC. The announcement was
  written on two such days; there are now seven.
- `listTnpCode`: zero on all 15 days, including before the cutover, and no caller in any of the
  63 repos searched.
- The ten `/proxy/old-report` routes: **zero across the entire 15-day window.** Over the same
  window `downloadTestOrderPDF` alone took 20,669 requests, which is what the ten are being
  measured against.

**What this evidence does not cover.** Log retention here stops at 15 days, so a job that runs
monthly is invisible to us, and the code search only covers repos cloned locally. That gap is
the whole reason this was announced two weeks ahead instead of simply deleted, and the counts
will be re-run on 2026-10-02 before the PR opens rather than relying on today's numbers.

**If you call any of these 13 routes, comment here before 2026-10-02** and it stays until you
have moved. For the `/proxy/grpc` routes the migration is to call the gRPC service directly, and
two things must come with you or the move is not equivalent: the JWT-to-gRPC metadata
construction in `src/proxy/proxy.service.ts` (`createMetadataForCoresampleV2` — it propagates
the caller's subject to core; it is not an ownership check), and for kit lookups the proto3
normalisation that fills an omitted `packages` with an empty array (leaving it out is Sentry
#68038). LIS-transformer-v2 PR #629 is the worked example.

**Unchanged plan.** 2026-10-02: re-check the logs, then open the removal PR for routes plus
config keys. 2026-10-09: merged, deployed, verified, ticket closed.

Full per-route removal and replacement list, including what deliberately stays behind (the
shared service layer and all of its environment keys — deleting those is the one way this PR
could cause an incident): [link to the Confluence page once published]

---

## Notes for Leo, not part of the comment

- The description's **Scope** section still lists only the three `/proxy/grpc` routes. If you
  want the widening reflected on the ticket face rather than only in a comment, that is a
  description edit — say the word and I will prepare it.
- QA twin **QH-7163** also describes three routes only, and will need the same widening.
- Posting mechanics: comments go through the MCP service account and render as "Jira agent".
  A description edit or a transition needs your own token.
