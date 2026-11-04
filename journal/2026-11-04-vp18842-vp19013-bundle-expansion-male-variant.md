---
date: 2026-11-04
tickets: [VP-18842, VP-19013, VP-19145]
tags: [emr-v2, place-order-api, bundle, pricing, getLegacyBundleDetails, male-variant, staging-e2e, grounding]
---

# 2026-11-04 — VP-18842 unblocked by a fact check, VP-19013 shipped with a fallback

## What happened
- Leo asked whether Rui's reply on VP-19145 ("getLegacyBundleDetails works for official bundles") was right. It was: prod
  `lis_pricing.promotions` stores official bundles with `customer_id = -1`; the 10-15 STM claim came from the legacy
  `lis_re.official_bundle_details` table. Leo's rule from this: every comment / judgment needs real-world evidence, re-verified at
  the time of writing, from the system actually in question (AGENTS.md principle 5 sub-bullet).
- VP-18842: expanded HL7 bundle lines into Place Order `sub_items` from pricing; meta_data flags moved to where order-management reads
  them. PR #528 -> staging, staging E2E with an official and a customer bundle, both placed with the members, cancelled.
- VP-19013: Leo's design — swap 868/869 -> 876/877 only when the twin is in the pricing catalog cache, otherwise base id. Verified the
  gate works because `getLegacyPackagePriceMapping` filters is_new + usd price, not orderability. PR #529 -> staging, E2E on the
  fallback branch (prod pricing has no 876/877). order-staging already swaps on its side (package 492 came back).
- Release PR #530 staging -> main opened; Leo merges. Jira both Dev In Progress until prod verified.

## Explored / ruled out
- Rebase of a pushed branch -> merged origin/staging instead (no force-push).
- Verifying staging orders in prod `lis_ordermanage` -> wrong: order-staging has its own snapshot DB; read back through the
  order-staging API (`/orders/info`, `/orders/package-tests`) from the staging pod with a JWT_SECRET_DEV token.
- x-choose-y guard from the bundle-details response -> impossible, no selection flag; documented, none on HL7 in 60 days.

## Leo's words
- "所有未來在 comment 和下判斷都需要真實世界做理論依據"
- "19013 不管 order 有沒有 876/877 都可以進 prod 不是嗎？寫一個 fallback 如果沒有就用原本的方式下單"
- "slack 要用中文, casual, 這應該要記好的" -> AGENTS.md Slack bullet; then "重新寫草稿" -> one question, no background.
