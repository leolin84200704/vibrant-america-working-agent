---
id: INCIDENT-20260910-emr-v2-di-crashloop
type: stm
category: technical
status: active
score: 0.9
base_weight: 0.9
created: 2026-09-10
updated: '2026-09-10'
links:
- VP-18034
- VP-18032
tags:
- incident
- emr-v2
- nest-di
- crashloop
- deploy
- vp-18034
summary: 'PR #412/#413 (VP-18034 wiring) crash-looped BOTH AKS emr-v2 pods on boot: RedisJtiStore
  had an optional interface-typed ctor param (client?: RedisSetNxClient) which Nest treats as a
  required provider. No traffic impact: maxUnavailable=0 kept the old pods (staging d67f029,
  prod 10ecea0) serving; deployments stuck 1/2. Root cause = no spec ever compiled the real
  module through Nest (all specs hand-construct or stub). Hotfix PR #414 (@Optional @Inject token
  + real-module compile spec) opened 23:12Z, awaiting Leo.'
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
