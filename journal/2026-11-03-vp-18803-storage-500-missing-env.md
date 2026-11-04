---
date: 2026-11-03
tickets: [VP-18803, VP-18802, LBS-1842]
category: process
severity: high
keywords: incident cut-over configmap DATABASE_URL_VA_INFO_MASTER trans prod storage 500 slack-tone verify-live prerequisite jira-comment-false
---

# VP-18803: storage routes 500 on trans prod after the batch 1 cut-over

## What happened
- 11-03: batch 1 LIS-Sample routes removed (#229, 17:54Z), ingress rewritten to trans, LIS-frontend #1305 base URL switched (20:02Z). From 23:32Z `GET /storage/racks/suggestions` returned 500 on trans prod: Prisma could not find `DATABASE_URL_VA_INFO_MASTER`. 27 real-user errors until the fix at 01:12Z (config patched + restart), last 500 at 01:13:48Z on a terminating pod.
- Mingxi forwarded Yuteng's attribution ("Leo's new change") at 16:48 PST. Leo asked the agent whether it was ours. It was.

## Why it was ours
- The missing env was recorded as a hard prerequisite three times (VP-18802 STM 10-15, LBS-1842 STM 10-16, repos.md). The 11-03 cut-over went ahead without re-reading the ConfigMap.
- Worse: the agent-written Jira blocker comment 199217 (11-03 11:39 PST, Leo's account) stated the key was present in prod, sourced from a colleague's earlier comment, never from `kubectl`. The STM even said "not re-verified" next to it.
- Yuteng's "first occurrence 10-20" was the Datadog 15-day retention edge; the boot warning existed since 10-14 and was dismissed as "known/expected" in every rollout check since.

## Fix (Leo: "ok 直接做")
- Leo re-ran `az login` (kubelogin token expired after 90 d idle). Values found in `sample/lis-sample-secret-prod` (STM had the names wrong: namespace is `sample`).
- Merge-patched both VA_INFO keys into `default/lis-trans-config` (backup first), rollout restart, live 200 through a port-forward with a self-signed HS256 token (`secretOrKeyProd`), Datadog clean after 01:15Z.
- Baseline PR #1095 merged on Leo's instruction, deploy-prod success, re-verified on the new image.

## Leo's Slack register (remember)
- His replies to Mingxi: "我看看", "我修一下", "修好了", "你看看". When the other person already knows the context, the message is the state change only. The agent's draft paragraph was wrong for this situation.

## Lessons (for dream)
1. A prerequisite written in memory is a blocker until re-read live in the session that moves traffic; the evidence (key names from `kubectl get cm`) goes into the message to Leo before the cut-over, not after.
2. Never let an agent-authored Jira comment assert a fact that was not verified in that session; "per X's comment" must be written as such.
3. "Known boot warning" is not a category to accept across rollouts; each known warning needs an owner and a due date tied to the ticket that will turn it into a failure.
4. Datadog Flex/15-day retention makes "first occurrence" claims unreliable; cross-check with deploy history and STM.
5. Slack reply to a colleague who is already in the thread: a few characters, action and result only.
