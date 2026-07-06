---
name: bug-triage
description: End-to-end triage of a Vibrant LIS bug ticket (VP-/LBS-). Use when given a bug ticket to diagnose — especially "results not received in EMR", "repush results", missing EMR orders, or any "customer says X never arrived" report. Trigger on "/bug-triage VP-xxxx", "triage 這張 bug", "result 沒到 EMR", "幫我 repush". Fully automates the result-repush class (diagnose → repush → verify); for code-bug classes it does NOT stop at diagnosis — it proceeds to a fix branch and a draft PR for human review. Never posts Jira comments or merges anything.
---

# Bug Triage — Vibrant LIS

Given a bug ticket id (`VP-xxxx` / `LBS-xxxx`), run the full loop: fetch → classify → diagnose → act (within the whitelist) or escalate to a draft PR / a well-formed question. The goal is that Leo only reviews conclusions and approves gated actions — never re-derives the diagnosis.

Related playbooks (load on demand, do not duplicate their content here):
- `long-term-memory/emr-integration.md` — result pipeline anatomy, silent-drop gap, repush mechanics
- `long-term-memory/patterns.md` — BullMQ queue inspection, hl7_file_input reprocess semantics
- `DailyJob/hl7_fail/triage_prompt.md` — order-intake (Type A/B/C) diagnosis + recovery, DB credentials, JWT recipe
- `lis-prod-change-gate` skill — mandatory for any code change or non-whitelisted prod write

## Step 0 — L4 verify + STM

1. Fetch the ticket via Atlassian MCP (`getJiraIssue`). Verify it is still open and the description matches what the requester actually needs (for LBS- tickets the real requester is in the description / `customerRequestType`, not the reporter field).
2. Check `storage/short_term_memory/{ticket_id}.md` and grep STM/LTM for the same accession/customer — recurring symptom means read the prior record first.
3. Create/append the STM file as you work (this skill's runs must leave an audit trail).

## Step 1 — Connectivity pre-flight (non-negotiable)

Almost every diagnosis below needs prod DB. **Before any query, prove connectivity explicitly** (e.g. `SELECT 1`).

- Outbound 3306 has been blocked in this sandbox since 2026-07-05. A connection failure or timeout is a **BLOCKED diagnosis**, never "no failing records". Empty result ≠ no failures — report the block loudly and stop the DB-dependent branch.
- Fallback path that has worked: the emr-v2 repo's local `.env` `DATABASE_URL` + `node_modules/mysql2` direct query (read-only). Try it before declaring blocked.

## Step 2 — Classify

| Class | Signal in ticket | Route |
|-------|------------------|-------|
| **A. Result not delivered / repush** | "no results in EMR", "repush", result_* keywords | Step 3 — full auto |
| **B. EMR order missing / intake failure** | "order not showing", hl7_file_input, emr_code_not_found | Step 4 — auto diagnose, whitelisted fixes |
| **C/D. Logic bug / API error** | reproducible wrong behavior, 4xx/5xx, calendar/billing logic | Step 5 — auto to draft PR |
| **E. Vendor / infra** | vendor outage, SFTP host down, "Dev Blocked" | Step 6 — diagnose + draft outreach |
| **Intent unclear** | scope ambiguous, conflicting AC | run `ticket-requirements-clarify` first |

## Step 3 — Class A: result repush (fully automated)

### Diagnose (read-only)

Resolve the sample/accession id(s) from the ticket, then walk this tree against `result_transmission_records`:

1. **0 rows for the sample** → the report_finished event never entered the pipeline. Known cause: integration created/enabled *after* the event (silent drop at `kafka-report-finished-listener`, offset committed, only a debug log). Confirm by comparing `ehr_integrations.created_at` / `result_enabled` flip time vs report-finished time. → Fix = manual generation (below). No backfill exists, so every pre-go-live report needs this.
2. **Rows in ERROR / stuck GENERATING** → pipeline entered but failed: check the error, and if generation is hanging inspect the BullMQ queue (`patterns.md` § BullMQ worker hang) — active-not-moving means worker hang, not stalled-job.
3. **Rows SUCCESS but customer says nothing arrived** → delivery-side: verify `ehr_integrations` sftp_result_path / msh06 / vendor config, then the customer SFTP itself. Config mismatch → Class B-style config fix; vendor side → Class E.

Pre-checks before any repush: integration `status=LIVE` and `result_enabled=1`, report actually finished, and the sample maps to the customer the ticket claims (wrong-customer symptoms → `emr-order-customer-resolution` skill).

### Act (whitelisted — execute without asking)

Repush = re-trigger result generation for the sample:
- `result.service.ts#generateResultHl7(sample_id)` via emr-v2's self-exposed gRPC `resultgeneration.ResultGenerationService` at `192.168.60.6:31317` (see `patterns.md` gRPC topology).
- Idempotent and low-risk; this is the Phase-1 whitelist action. Do NOT widen it: anything requiring an `UPDATE`/`DELETE` on prod data outside this is gated (Step 7).

### Post-verify (mandatory, on live state)

After repush, re-query `result_transmission_records` for a new SUCCESS row and confirm the file landed (SFTP listing when reachable). Verify **every** sample you repushed, not a spot-check. A repush you didn't post-verify is not done.

## Step 4 — Class B: order intake failure

Diagnosis playbook = `DailyJob/hl7_fail/triage_prompt.md` (Type A/B/C classification, credentials, recovery recipe). Additional routing:

- Decide **which processor owns the failure** before touching `retry_num`: `parse_finished=0` + customer_not_found + `retry_num=0` → Java cron path, `SET retry_num=3` reprocess applies (VP-16765). emr-v2 counts retry_num *down* from 5 and re-drives from SFTP scans — the reprocess trick does not apply there (`patterns.md` § hl7_file_input Reprocess).
- Whitelisted: reprocess flag flips per the playbook, and the manual payment+order recovery flow exactly as scripted in `triage_prompt.md`.
- Order replay is **not idempotent**: before any replay check `lis_core_v7.sample` for an already-created sample, and when backfilling `hl7_file_input.sample_id` always insert the matching `emr_sample` row (emr-integration.md § order replay 安全準則). Never ask a vendor to resend order files — that duplicates orders.
- Config INSERTs (new provider row / mapping following an established pattern) → prepare the exact SQL + the past ticket it mirrors, then gate (Step 7).

## Step 5 — Class C/D: code bug → draft PR (do not stop at diagnosis)

Human intervention here means *review*, not *hand-off*. The skill's job is to arrive at a reviewable PR:

1. Root-cause against the real repo (route via `long-term-memory/ticket-routing.md`; EMR work is always `lis-backend-emr-v2`, never EMR-Backend).
2. Walk `lis-prod-change-gate` in full — branch `bugfix/leo/{ticket_id}`, 4-part analysis, config-yaml coupling, tests covering the new branches.
3. Push the branch and open a **draft PR** (`gh pr create --draft`), body in English with the diagnosis chain + test evidence, ending with the standard attribution.
4. The PR is the deliverable. Merge/deploy stays with Leo — never merge, never push staging. Deploy-bound work targets `stage_test` via PR only.
5. Draft (never post) a Jira comment linking the PR.

## Step 6 — Class E: vendor / infra

Diagnose as far as our side allows, then draft the outreach message (English) with the exact evidence the vendor needs (file names, timestamps, MSH.10 ids). For incidents: preserve evidence **before** any restart (`kubectl` logs + describe first — prod-change-gate Gate 9).

## Step 7 — HITL gates (what still pauses for Leo)

Pause and present, instead of executing:
- Any prod `UPDATE`/`DELETE`/`INSERT` outside the Step 3/4 whitelist → present the exact SQL, bounded WHERE, expected row count (prod-change-gate Gate 7).
- Merge / deploy decisions (always).
- Sending anything external: Jira comments and Slack messages are **drafted only**.
- Intent questions only a PM/requester can answer — ask them well (one recommended default per question, not open menus).

## Step 8 — Report (zh-TW)

```
## Ticket: {id} - {title}
### 分類與診斷鏈          ← the decision-tree path taken, with query evidence
### 已執行動作 + post-verify 結果   ← every whitelisted action, verified
### 待批准動作            ← exact SQL / PR link awaiting review
### 起草的 comment/訊息    ← Jira/Slack drafts, not sent
```

Also append the run to the STM file (category `emr_integration` for A/B, `technical` for C/D) and note any *new* diagnosis pattern worth promoting to LTM — flag it for the dream pipeline rather than editing LTM directly.
