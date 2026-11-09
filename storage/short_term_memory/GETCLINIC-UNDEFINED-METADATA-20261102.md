---
id: GETCLINIC-UNDEFINED-METADATA-20261102
type: stm
category: technical
status: done
score: 0.0921
base_weight: 0.9
created: 2026-11-02
updated: 2026-11-03
summary: transv2 getClinic 'Database or server error' on staging = grpc call with
  undefined metadata (since
links: []
tags:
- transv2
- calendar
- grpc
- dd-trace
- staging
---

# getClinic "Database or server error" on staging (no ticket; colleague report via Leo)

## Root cause
- transv2 `ClinicService.getClinicById/getClinicPatients` pass `undefined` metadata without context; `buildRpcMetadata` also returned `undefined` on fallback. Nest forwards `(req, undefined)` to grpc-js 1.13.4 -> TypeError "reading 'interceptors'" in makeUnaryRequest -> resolver maps to "Database or server error". All clinics affected.
- Introduced by #451 (2026-05-12, Yuxuan), not Leo's original getClinic (e43de569 called GetClinicByID(req) with one arg).
- Masked wherever dd-trace is injected (its grpc instrumentation normalizes args). The 11-01 staging pod had no Datadog init containers; prod pods did. After the #748 rollout the new -st pod has dd injection again.
- Nest `Logger` output from ClinicService does not reach pod stdout; reproduced in-pod instead (self-minted dev HS256 token -> localhost:3390/graphql; Nest ClientGrpcProxy probe with DD_TRACE_ENABLED=false to see the unmasked behavior).

## Fix / status
- #748 -> stage_test merged by agent, deployed bb423bc, verified: full GetClinic query OK for 150105/10136; dd off: undefined FAIL, new Metadata() OK.
- #749 -> main (cherry-pick, head 25abb83), waiting on Leo merge. Jest 95/95 suites.
- Also updated VP-17825 calendar.service.spec assertion that pinned `undefined` metadata.

### [2026-11-03] prod verified
- Leo merged #749 (a6c80ca, 18:47Z); frontend-service-graphql run 41697222026 success; all 3 prod replicas on a6c80ca.
- In prod pod: dist contains the fix; deployed ClinicService.getClinicById with DD_TRACE_ENABLED=false -> 150105 / 10136 OK. No self-minted prod JWT used.
