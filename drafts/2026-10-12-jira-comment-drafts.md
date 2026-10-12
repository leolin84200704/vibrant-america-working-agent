# Jira comment drafts 2026-10-12 (NOT posted — Leo posts or edits)

## VP-18770
Shipped to staging (PR #474, merged into staging 2026-10-12; release PR #476 staging -> main pending).

Core V1 (lis package, :30276) and Core V2 (coresamples_service) calls now carry `authorization: Bearer <RS256 service token>` (kid oauth-jwt-rsa), `service-name` and `x-request-id`, attached by a grpc-js client interceptor on those clients only; results-grpc keeps its existing HS256 token and shipping is unchanged. RS256 unavailable -> HS256; neither -> the call goes out without a token as before, counted and reported. `CORE_RPC_RS256=off` (ConfigMap, no deploy) sends HS256 only.

Staging check: Core V2 token_check for `lis-backend-emr-v2-production` went from `token_class=none` to `service` on the triggered GetSampleRelevantInfo calls. Note for Core: the emr-v2 OAuth2 client's token identity is `internal_user_name: "trans v2"`; `service-name` is what identifies emr-v2 (see the separate note to Zhibin).

## VP-18771
Confirmed the open question first: the gRPC server was effectively unauthenticated — `connectMicroservice()` is called without `inheritAppConfig`, so the global JwtAuthGuard never ran on RPC (prod served 1152 generateResultHl7 calls in 7 days with no token check).

Shipped to staging (PR #475; release PR #476 pending): `GrpcAuthGuard` on both gRPC controllers reads the token from gRPC metadata, accepts HS256 (JWT_SECRET) and RS256 (oauth-jwt-rsa public key) chosen by the token's alg with `algorithms` pinned, rejects `none`, and requires `internal_user_name`. Log-only by default: every call is served and one `grpc_auth_check` line records method, service-name, alg, outcome and identity. `AUTH_GRPC_MODE=enforce` (ConfigMap) switches to gRPC UNAUTHENTICATED.

Staging check (grpcurl GetResultStatus): no token, HS256, RS256 and alg=none were all served and logged as missing_token / ok / invalid_token / bad_alg. The RS256 invalid_token on staging is the staging ConfigMap's FHIR_JWT_RS256_PUBLIC_KEY being a different key from prod (the prod key verifies the token) — to fix before enforce on staging.

Next: run log-only for at least a week, build the caller histogram from the log line, then flip enforce.

## VP-18480
Attribution window closed early on Leo's call (12.8 days, ~338k requests, 66 live route+method pairs). Deliverables drafted for review before they go on the roadmap page: caller table per family, classification (PHI-gated / aggregation / service-to-service / dead), target home (staff families -> trans v1 in-process; /patients/v2/kits -> trans v2 in-process per VP-18482; two new TransService RPCs for LIS-Shipping and the results family), 10-row consumer runbook, sizing (~106 SP beyond VP-18482, Phase B on the critical path for storage).

18 OpenAPI operations had zero traffic and are being removed now: LIS-Sample PR #208 (master) awaiting review, PR #209 (dev) merged. Side finding tracked as VP-18782 (full Bearer token and request body logged to Datadog on every request).
