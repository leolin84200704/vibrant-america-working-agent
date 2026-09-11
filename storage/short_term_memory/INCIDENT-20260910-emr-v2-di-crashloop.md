---
id: INCIDENT-20260910-emr-v2-di-crashloop
type: stm
category: technical
status: resolved
follow_up: factory PRs
score: 0.7763
base_weight: 0.9
created: 2026-09-10
updated: '2026-09-11'
links:
- INCIDENT-20260518
- INCIDENT-20260601-sftp-hang
- INCIDENT-20260604
- INCIDENT-20260817-onprem-deploy-freeze
- INCIDENT-20260908-grpc-dead-node-ip
- QH-1104
- QH-1130
- QH-1159
- QH-1591
- QH-1775
- QH-211
- QH-2259
- QH-680
- QH-862
- QH-918
- QH-919
- TRANS-OPTIMIZATION-20260911
- VP-15460
- VP-16169
- VP-16172
- VP-16232
- VP-16391
- VP-16499
- VP-16513
- VP-16514
- VP-16516
- VP-16520
- VP-16521
- VP-16629
- VP-16785
- VP-16787
- VP-16859
- VP-16921
- VP-16945
- VP-16968
- VP-17065
- VP-17217
- VP-17222
- VP-17312
- VP-17422
- VP-17559
- VP-17577
- VP-17714
- VP-17753
- VP-17754
- VP-17755
- VP-17765
- VP-17766
- VP-17825
- VP-17868
- VP-17870
- VP-18032
- VP-18034
- VP-18048
- VP-18050
- VP-9299
- business-model
- business-model-deep
- failures
- repo-catalog
- repos
tags:
- incident
- emr-v2
- nest-di
- crashloop
- deploy
- vp-18034
summary: 'PR #412/#413 (VP-18034 wiring) crash-looped BOTH AKS emr-v2 pods on boot:
  RedisJtiStore had an optional interface-typed ctor param (client?: RedisSetNxClient)
  which Nest treats as a required provider. No traffic impact: maxUnavailable=0 kept
  the old pods (staging d67f029, prod 10ecea0) serving; deployments stuck 1/2. Root
  cause = no spec ever compiled the real module through Nest (all specs hand-construct
  or stub). Hotfix PR #414 (@Optional @Inject token + real-module compile spec) opened
  23:12Z, awaiting Leo.'
jira_status: n/a
---

# INCIDENT-20260910 — emr-v2 new pods CrashLoopBackOff after VP-18034 wiring

## Timeline (UTC, 2026-09-10)
- 22:45 #412 (feature/leo/VP-18034 → staging, e57641b) merged by Leo; 22:48 #413 staging → main (4b6f619).
- 22:57 Jenkins rolled new pods on both AKS deployments (ns emr-v2). Both new containers exit at
  Nest injector time: `UnknownDependenciesException: Nest can't resolve dependencies of the
  RedisJtiStore (ConfigService, ?)`. 6 restarts each by 23:07, CrashLoopBackOff (back-off 5m).
- Old pods `lis-emr-v2-deployment-prod-c4549bc86-r96rj` / `-staging-544ddb486f-7w6k2` stayed
  Running + Ready (strategy maxSurge 1 / maxUnavailable 0) — `/api/v1/health` 200 via the old
  prod pod at 23:08. No customer-visible impact observed; rollout stuck at ready=1 unavailable=1.
- 23:11 Leo merged #414 → staging (d8e4c9b); 23:12 #415 staging → main (c6d823a). Jenkins roll
  awaited; the deploy monitor now also alarms on "image switched but not ready after 3 min" and
  on restartCount > 0 for the new pods.
- 23:21 hotfix pods up (d8e4c9b / c6d823a), old ReplicaSets retired, 0 restarts, health 200.
  RESOLVED. Follow-on (not a crash): first T request per pod start was 503 store_unavailable
  (ioredis lazyConnect + enableOfflineQueue=false) → #416 → live 23:41Z, verified 13/13.
- 23:07 detected by the agent's own "ok 了嗎" check (the deploy monitor only reported "not ready
  yet"; a 10-minute 1/2 should itself have been treated as a signal).
- 23:09 logs dumped to scratchpad before anything else (Gate 9). 23:10 reproduced locally with a
  new spec that compiles the REAL module (fails with the identical message). 23:12 hotfix PR #414
  → staging, head b7899f3, tests 43/43, build OK.

## Root cause
`RedisJtiStore` constructor: `constructor(config: ConfigService, client?: RedisSetNxClient)`.
`RedisSetNxClient` is an interface → `emitDecoratorMetadata` records `Object` for that parameter
→ Nest looks for a provider registered under `Object`, finds none, throws for the whole app.
Harmless in PR-A (#410) because nothing imported the module; fatal on the first import (#412).

## Why tests were green
- platform-assertion specs: hand-construct `new RedisJtiStore(config, fakeClient)`.
- order-intake specs: `new OrderIntakeController(intakeService, platformAssertion)` by hand.
- order-status.routes.spec (the only Nest TestingModule) got `{ provide: PlatformAssertionService,
  useValue: stub }` — so the real module's providers were never resolved by the injector.
- `nest build` / `tsc` cannot see DI metadata problems.

## Fix (PR #414)
- `@Optional() @Inject(JTI_REDIS_CLIENT) client?` with an explicit Symbol token nobody provides in
  production → resolves undefined → store builds its own lazyConnect ioredis client as designed.
- New `platform-assertion.module.spec.ts`: `Test.createTestingModule({ imports: [ConfigModule
  .forRoot({ignoreEnvFile:true,isGlobal:true}), PlatformAssertionModule] }).compile()` and resolve
  `PlatformAssertionService` + `JTI_STORE`. Reproduces the prod error pre-fix.

## Options given to Leo
1. Merge #414 → staging → main (Jenkins ~11 min per env) — fix forward.
2. Meanwhile or instead: `kubectl rollout undo deployment/lis-emr-v2-deployment-{prod,staging}
   -n emr-v2` returns each deployment to the previous ReplicaSet (10ecea0 / d67f029, both of which
   contain PR-A only) in seconds; Jenkins will re-roll on the next merge anyway. NOT executed —
   prod state change, Leo decides.

## Lessons (candidates for ENGINEERING-LESSONS / patterns)
- **A green unit run says nothing about Nest DI.** Any PR that adds a provider or a constructor
  dependency needs at least one spec that compiles the REAL module (or app module) through
  `Test.createTestingModule`. Stubbing the new service in the one existing TestingModule spec
  (which I did, to make it pass) is exactly how this slipped through.
- **Optional constructor params in @Injectable classes must be `@Optional() @Inject(TOKEN)`**;
  a bare `param?: Interface` is a required `Object` dependency at runtime.
- **A rollout stuck at 1/2 for >3 min IS the alarm**, not "still deploying". The deploy monitor
  should emit on `readyReplicas < replicas` persisting past the normal ~2 min, and on any
  container restartCount > 0 for the new ReplicaSet.
- Gate 6 "verify on live" was applied to PR-A (dist present, health 200) but PR-A had no import;
  the equivalent check for PR-B had to wait for the roll — which is when it broke. A local
  `nest start` smoke (or the module-compile spec) before push would have caught it in 5 seconds.

## Leo 2026-09-10 16:50: "這是嚴重的失誤，要記起教訓" — enforcement proposal (for the FACTORY session)

BOOTSTRAP §89: framework / hooks / lesson distillation are done in a `$FACTORY` session, not
in the instance session. Everything the factory session needs is below; nothing else is missing.

### Measured facts that make a level-5 mechanism possible
- `nest build && env -i PATH HOME NODE_ENV=test node dist/main.js` with NO env, on the crashing
  build 4b6f619: 6 modules "dependencies initialized", then `UnknownDependenciesException ...
  RedisJtiStore` within ~1 s. On the fixed build e2252a1: 14 modules, 0 DI errors, dies on
  `JWT_SECRET environment variable is required`.
- With `.env.example` keys set to placeholders (+ JWT_SECRET/ADOBE dummies, ORDER_INTAKE_MODE
  disabled, PORT 39999): 15 modules, 0 DI errors, dies on `Missing required configuration:
  CLICKHOUSE_HOST` — i.e. the DI graph is fully resolved before the first hard config check.
- So the discriminator is deterministic and needs no network: PASS = no
  `UnknownDependenciesException|can't resolve dependencies` in the first 30 s; FAIL otherwise.
  Whether it reaches "Nest application successfully started" is NOT the criterion (it needs DB).

### Proposed lesson entries (CONTRIBUTING format, ≤50-char principle + 適用)
1. **DI 圖要用真容器解析一次再 push** — 新增 provider / constructor 依賴的變更，push 前必有一個
   spec 用 `Test.createTestingModule` 編譯真 module，或跑一次 boot smoke；手動 `new` 與 stub 掉新
   service 的 TestingModule 都測不到 injector。適用: NestJS/Spring/Angular 類 DI 框架的任何
   provider 變更；在唯一的 TestingModule spec 裡「stub 掉新依賴讓它過」就是這條的反例。
   `enforced-by:` → framework/hooks/validate-nest-di-smoke.sh（待建，見下）。
2. **可選建構子參數要 `@Optional() @Inject(TOKEN)`** — `param?: Interface` 在 Nest 是必要的 `Object`
   依賴，整個 app 起不來。適用: 為測試留「可注入假物件」口的 @Injectable 類。
3. **冷啟動後第一個請求是獨立的測試案例** — 部署驗證要在新 pod 上打第一發，lazy connect / 連線
   池 / 快取預熱的 bug 只在那一發出現。適用: 任何 lazyConnect、offline-queue、warm-up 相關設定；
   ioredis 的 `enableOfflineQueue:false` + `lazyConnect` 就是這樣第一發必 503。

### Proposed mechanism (level 5, PreToolUse hook on `git push`, factory repo)
- `framework/hooks/validate-nest-di-smoke.sh`: on `git push` from a repo whose package.json has
  `@nestjs/core`, require marker `.git/di-smoke-ok-<HEAD sha>`; else exit 2 with the one-liner to
  produce it. Marker is written by `framework/hooks/lib/nest-di-smoke.sh`: `nest build`, boot
  `dist/main.js` for 30 s with `env -i` + `.env.example` placeholders, grep the DI-error pattern,
  write marker on PASS. Test file `framework/hooks/tests/validate-nest-di-smoke.test.sh` with a
  fake repo (marker present / absent / stale sha). Wire in each Nest product repo's
  `.claude/settings.local.json` like the other hooks. Product-repo-side alternative (needs team
  acceptance, so only as a proposal): `npm run smoke:di` + CI step.
- Second-layer, cheaper, per-PR habit until the hook exists: the module-compile spec pattern
  (`platform-assertion.module.spec.ts`) for every new module.

## [2026-09-11 10:20] Factory session — proposal executed
- PR #74 `lesson/lis/di-graph-real-container-before-push`: lesson entry (enforced-by) + `framework/githooks/lib/nest-di-smoke.sh`
  wired into `framework/githooks/pre-push` after "build OK" for gated Nest repos; `validate-git-push.sh` now blocks
  `git push --no-verify` for the agent. Deviation from the proposal above: no PreToolUse marker hook — the factory
  pre-push build gate is the gate that passed #412, so the smoke lives there.
- Measured on real builds (scratch worktrees): 4b6f619 FAIL in 3 s (6 modules), origin/main 5e67339 PASS in 2 s
  (40 modules); no-env run also PASS 40 modules, so `.env.example` is not read by default (it carries real gRPC/Kafka hosts).
- PR #75 lesson 2 (`@Optional() @Inject(TOKEN)`), PR #76 lesson 3 (first request after cold start) — one lesson per PR.
- Open for Leo: whether to add the other Nest repos (transformer-v2, results-web, ...) to `BUILD_GATE_REPOS`.

## [2026-09-11 11:00] Gate expanded to every LIS Nest repo (factory PR #77, merged by agent under Leo's session authorisation)
- `BUILD_GATE_REPOS` now: emr-v2, transformer-v2, transformer, coreSamples, dashboard, results-web, results-core,
  results-grpc, Sample, interactive-report, notification-center, setting-consumer, Shipping, Portal-Calendar.
  Every `git push` from these repos on this Mac runs prisma generate (repo script preferred) -> `npm run build` ->
  Nest DI smoke. The agent cannot `git push --no-verify` (PreToolUse hook); Leo can.
- Smoke evidence is now logger-independent (`node -r nest-di-smoke-preload.js` wraps NestFactory.create) — needed
  because transformer-v2 boots with `logger: false`.
- **Per-machine env files** live in `~/.config/nest-di-smoke/<origin-repo>.env` (outside every product repo, shared by
  all worktrees). Created on this Mac: `LIS-backend-coreSamples.env` (JWT_SECRET, JWT_EXPIRATION_TIME, run_mode=app,
  unreachable AZURE_REDIS_*, and `DI_SMOKE_ALLOW_SILENT=1` because its DI phase awaits Redis/Kafka). If a push in
  another repo dies INCONCLUSIVE with "Config validation error", the report prints the file path and keys to add.
- Known state per repo at gate time: transformer-v2 PASS; coreSamples accepted (silent); setting-consumer / Shipping /
  Portal-Calendar tsc OK in the real clones; **LIS-transformer's clone is missing `@google-cloud/bigquery`
  (declared, not installed) — run `npm install` there before the next push or the build gate will block it**;
  dashboard / results-* / Sample / interactive-report / notification-center have no node_modules here (unverified).
- Dream pipeline: yesterday's (09-10) run FAILED after 3 attempts (API errors). Manual run started 10:24 PDT today,
  detached with nohup; log `~/.lis-agent-state/dream/manual-2026-09-11.out`.
