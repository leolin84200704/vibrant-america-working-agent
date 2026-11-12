---
id: 2026-11-12-vp19162-sandbox-simulator-partial
type: journal
date: 2026-11-12
tickets: [VP-19162, VP-19168, VP-19169, VP-19163, VP-19164]
tags: [sandbox, simulator, partner-api, issue-system, emr-v2, get-orders]
---
# VP-19162: sandbox simulator partial build, draft PR #542

Trigger: Leo approved the 11-09 plan to build the unblocked part while the ticket stays Dev Blocked on
VP-19168 (Shipping) and VP-19169 (Core).

Done: emr-v2 feature/leo/VP-19162 (4d6b24d) -> draft PR #542 to staging. POST sandbox/orders/simulate (plus
order-intake/sandbox/simulate on the existing passthrough), validation, shared order resolution
(OrderStatusService.resolveForSimulation), forward-only planner, issues set/clear via the Issue System, scenario
timer, rate limit. Shipping/Core are interfaces that answer 503 with the pending ticket ids before any write.

Probe first, then code: raised one billing issue (type 84) on staging sample 2554405 through Issue System :30072 with
the trimmed proto, saw it in the staging pod's GET /orders, resolved it, saw it clear. This confirmed comment 199852
before the code depended on it. The sample is back to no open issues; pod scratch files removed.

Pitfall: after UserResolveIssue the Issue System is correct at once, but GET /orders keeps the exception for 1-2
minutes (base-report cache). Reading "current issues" from GET /orders would raise duplicates; read the Issue System.
Second pitfall: UserResolveIssue with object+type ignores issue_id and resolves the first unresolved issue of the type,
so clearing N issues of one type needs N calls.

Gate notes: four new env vars, all with code-side defaults; the env guard warns (not in live ConfigMap), recorded in
the PR. Verified every live emr-v2 ConfigMap: prod is ENVIRONMENT=production, so the route is 404 there.

Next: Leo reviews #542. After staging merge, AC6/AC8/AC10 live on api-sandbox. Real writers when VP-19168/19169 land.
