# VP-18485 — Jira comment draft (Leo posts; @ the boss where marked)

@<boss> — picking up your ConfigMap/Secret suggestion. Where things stand and what I propose:

**What is already done**
- The hard-coded credential was in `src/redis_s.ts`, a file nothing imported (dead code). It was deleted in LIS-transformer #843 (main) / #844 (stage_test), both deployed 2026-09-29. `main` now contains no Redis credential. LIS-setting-consumer carried the same literal; Ray's #186 removed it the same day.
- The live Redis clients (`src/redis.ts`, `app.module.ts`, calendar) already read every endpoint and credential from env, and the env comes from the AKS ConfigMap `lis-trans-config` (`Azure_redis_host/port/pass`, `REDIS_ADDR/PORT`). So the endpoint is not in the code today; the remaining problem is where the credentials sit.
- Still open from the ticket: rotating the on-prem Redis password (192.168.60.9:4646). Whoever operates that instance needs to do it; I can verify afterwards that the old value no longer authenticates.

**Gap the suggestion points at**
- `lis-trans-config` (ConfigMap, plain text) currently holds 15 credential-valued keys, including `Azure_redis_pass`, `OAUTH2_CLIENT_SECRET`, `HUBSPOT_API_KEY`, `GOOGLE_CLIENT_SECRET`, `OUTLOOK_CLIENT_SECRET`, `consul_token`, `cloud_kafka_ssl_password`, `secretOrKeyDev/Prod`, `token`, `patientReportToken`, `create_patientv2_token`, `getSubmittedBarcodesInfo_questionnaire_token`, `oauth_client_secret`, `TURNSTILE_SECRET`. `lis-trans-secret` holds only 2 (`BIGQUERY_CREDENTIALS_JSON`, `TURNSTILE_SECRET_KEY`).
- The repo yaml is not a usable source today: `lis-trans-k8env.yml` has 6 keys (live ConfigMap has 149) with a stale `REDIS_ADDR`, and `lis-trans-secret.yml` commits the live Turnstile secret in plaintext (`stringData`), which is the same class of problem this ticket is about.

**Proposal (same shape as LIS-interactive-report `k8s/{production,staging}/{configmap,secret}.yaml`)**
1. Move the 15 credential keys from `lis-trans-config` / `-st` into `lis-trans-secret` (add to the Secret, verify in-pod, then remove from the ConfigMap). No code change: `lis-trans-deployment` already uses `envFrom` for both, and a key resolves the same way from either source.
2. Replace the committed yaml with templates: a full non-secret `configmap.yaml` (generated from the live ConfigMap minus the credential keys) and a `secret.yaml` with placeholder values plus the `kubectl create secret ... --from-literal` recipe in a comment, as the report service does. Rotate the Turnstile key since its value is in git history.
3. Rotation of the on-prem Redis password as already listed in the ticket.

Two questions before I start: (a) is it OK to widen this ticket to 1–2 above, or should that be a separate ticket under VP-18260? (b) who owns the on-prem Redis instance for the rotation?
