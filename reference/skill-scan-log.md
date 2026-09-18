# Weekly skill scan log (skillsmp / GitHub)

> Results of the twice-weekly skill scan (hook: `~/.claude/hooks/skillsmp-reminder.sh`).
> Scope filter: DB migration safety, test/build verification, code review, schema/query
> analysis, backend reliability/observability, repeated-rules-to-git-hooks.
> Hard-excluded: vibe-coder, frontend, content, autonomous-loop (ralph-wiggum class).
> One dated entry per scan, newest first. Watchlist at the top carries forward.

## Watchlist (carry-forward)

| Added | Tool | Why watching | Trigger to adopt |
|---|---|---|---|
| 2026-09-18 | [johnqtcg/awesome-skills mysql-migration](https://github.com/johnqtcg/awesome-skills/tree/main/skills/mysql-migration) | Only MySQL-specific migration-safety skill found that ships a deterministic checker: `scripts/lint_migration.py` (~1.1k lines, stdlib only, 30 checks MM001-MM030) — INSTANT/INPLACE/COPY version gates against the EXACT server version, LOCK clause validation, `lock_wait_timeout` session guards, FK+INPLACE, VARCHAR byte-band crossing, `IF NOT EXISTS` misuse; `--format json --baseline --fail-on`. Fits emr-v2's manual-DDL Azure MySQL (prod = 8.0.45-azure). Caveats: 30 stars, regex-based (no schema reconstruction), DDL only — does NOT cover UPDATE/DELETE data fixes, which is our biggest incident class. | Next manual prod ALTER on lis_emr / lisportal: run the linter with `--mysql-version 8.0.45` as a Gate step in `lis-prod-change-gate`; if it catches anything real, wire it as a pre-commit hook on `*.sql` migration files. |
| 2026-09-18 | [planetscale/database-skills mysql](https://github.com/planetscale/database-skills/tree/main/skills/mysql) | 676 stars, vendor-maintained. Reference-grade (no scripts): `references/online-ddl.md` (algorithm/lock decision table, 8.0.28/8.0.29 gates, metadata-lock commit-phase caveat, gh-ost vs pt-osc), `deadlocks.md`, `row-locking-gotchas.md`, `explain-analysis.md`. Generic MySQL 8, applies to Azure MySQL; PlanetScale hosting plug is skippable. | Load the online-ddl / row-locking references on demand during schema or UPDATE-WHERE-JOIN review; candidate source text if we ever write a MySQL section into `lis-prod-change-gate`. |
| 2026-08-18 | [Hainrixz/claude-db](https://github.com/Hainrixz/claude-db) | Schema audit (23 modules, reproducible evidence, read-only default) + lock-aware migration generation (concurrent index builds, `NOT VALID`+`VALIDATE`, expand/contract). Substantive, not a prompt wrapper. Caveats: Postgres-idiom techniques (limited value for emr-v2's manual-DDL MySQL; relevant to transformer-v2 calendar Postgres); early-stage (5 commits / 18 stars). | Next large calendar (Postgres) schema change — run its audit as a pre-review pass and evaluate. |

## 2026-09-18 scan

- **Prod fact surfaced by the scan**: lisportalprod2 `@@lock_wait_timeout` = 31536000 (MySQL default, 1 year) and `@@innodb_lock_wait_timeout` = 50. A manual DDL that hits a metadata lock will queue indefinitely and stack every later query on that table behind it. Independent of any skill: prefix manual prod DDL with `SET SESSION lock_wait_timeout = 5` (fail fast) — proposed as a `lis-prod-change-gate` addition, pending Leo.
- **mysql-migration (johnqtcg)** → watchlist (above). Strongest DB-safety candidate since the scan started: first one with runnable, version-aware checks instead of a prose checklist.
- **planetscale/database-skills mysql** → watchlist (above) as reference text.
- Reviewed and rejected:
  - [mattpocock/skills git-guardrails-claude-code](https://github.com/mattpocock/skills/blob/main/skills/misc/git-guardrails-claude-code/SKILL.md) — PreToolUse block of push / reset --hard / clean / branch -D. We already enforce the same set via factory `validate-git-push.sh` + `validate-git-destructive.sh`; nothing new.
  - [mechemsi/claude-template db-migration-safety](https://github.com/mechemsi/claude-template) — expand/contract principles, ORM cookbook; single MySQL sentence, no scripts. Already covered by our Schema-migration hot lesson.
  - [alekspetrov/navigator database-migration](https://github.com/alekspetrov/navigator/blob/main/skills/database-migration/SKILL.md) — generates ORM migration files (Knex/Prisma/TypeORM/Drizzle) with a confirm step; our prod DBs are not ORM-managed.
  - [paultyng/skill-issue review-database](https://github.com/paultyng/skill-issue/blob/main/skills/review-database/SKILL.md) — Go-centric, runs squawk for Postgres only; MySQL side is a checklist.
  - [MariaDB/skills mariadb-query-optimization](https://github.com/MariaDB/skills/blob/main/mariadb-query-optimization/SKILL.md) — official but MariaDB 11.8 syntax (`ANALYZE`, `IGNORED`, `LIMIT ROWS EXAMINED`) diverges from MySQL 8.
  - [datadog-labs/agent-skills](https://github.com/datadog-labs/agent-skills) (172★, official) and [DataDog/datadog-api-claude-plugin](https://github.com/DataDog/datadog-api-claude-plugin) (46 agents) — both drive the `pup` CLI with API/APP keys; dd-logs prescribes command order, not triage methodology. Our Datadog MCP already covers read paths; the plugin's value is write ops (monitors/dashboards) we do not delegate to agents.
  - [freddo1503/claude-pre-commit](https://github.com/freddo1503/claude-pre-commit) — lints SKILL.md / settings.json; 3 stars, v0.1.0, validation still WIP.
- Pattern noted, not a skill: "PreToolUse on `git push` runs lint+tests, exit 2 blocks" (several blogs). Our **Test before push** hot lesson still has no `enforced-by:`; an in-house hook scoped to emr-v2/transformer repos running the affected test subset is the ENFORCEMENT-LADDER move. Filed as idea for Leo.

## 2026-08-18 scan

- **claude-db** → watchlist (above).
- Reviewed and rejected:
  - [anthroos/claude-code-review-skill](https://github.com/anthroos/claude-code-review-skill) (38★, 280+ checks) — checklist-style review, overlaps built-in `/code-review` + cursor-bot on our PRs; categories skew frontend (accessibility/React).
  - [aidankinzett/claude-git-pr-skill](https://github.com/aidankinzett/claude-git-pr-skill) — agent posts PR reviews directly; opposite of our "agent drafts, Leo reviews" model.
  - [disler/claude-code-hooks-multi-agent-observability](https://github.com/disler/claude-code-hooks-multi-agent-observability) — observability of Claude Code agents themselves via hook events; conceptually interesting for the dream/triage fleet but requires running a server; ROI not there.
- Everything else: directories/listicles or "community-needed" placeholders.

## 2026-08-14 scan

- No adoptable findings. DB-migration and SQL-analysis entries in major lists were
  "community-needed" placeholders; concrete code-review/verification candidates were the
  long-known [obra/superpowers](https://github.com/obra/superpowers) set (systematic-debugging,
  verification-before-completion) — not new; one small-repo pr-review skill with no adoption
  signal.
