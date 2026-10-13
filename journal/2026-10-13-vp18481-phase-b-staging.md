---
date: 2026-10-13
ticket: VP-18481
type: journal
---
# VP-18481 Phase B: staging cutover day

- Tianhao created the staging Service Bus entities; verified with `az ... show`; switches on; five replay scenarios passed live; week-long soak started.
- Shutdown rabbit hole: `npm run` as PID 1 swallowed SIGTERM -> node as PID 1 + enableShutdownHooks hung 48 s -> root cause = PID 1 ignores Nest's re-raised signal (reproduced in a bare node:22-alpine pod) -> explicit `process.exit()` after `app.close()` with a 10 s deadline closes in 3 s. Dropped the per-hook trace PR once the premise fell. `Aborted_clients` is useless for Prisma.
- Leo's words: "告訴我需要Tianhao 怎麼建立service bus的東西" / "Tianhao 建好了，請你核對後繼續" / "開 enableShutdownHooks 的 PR，Jira comment 也發" / "幫我連上Atlassian integration, 發現的問題也要一起解掉" / "以後做完需要我 merge 都要給我 PR".
- New working rule from Leo: any PR he has to merge must be reported with its URL.
- Excluded: merging the factory lesson PR myself (CONTRIBUTING: Leo merges); changing Service Bus entity properties (no Contributor role); pushing the LIS-Sample doc fix (no access, patch handed off).
