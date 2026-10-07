# hl7_triage_graph - LangGraph port of the HL7 daily triage

Replaces the prompt-driven `run_triage.sh` -> `claude -p triage_prompt.md` loop
with a graph whose deterministic steps are plain Python and whose only LLM
node writes the narrative from facts the graph already established.

```
START -> preflight -+-> fetch_failed -+-> classify -> resolve_customer -> lookup_codes -> write_report -> send_mail -> END
                    |                 '-> write_report (no records) ------------------------^
                    '-> write_blocked_report -> send_mail -> END
```

| node | what it does | source of truth |
|---|---|---|
| preflight | TCP check on the prod MySQL host; missing password or VPN-down becomes a BLOCKED report that is still mailed | `run_triage.sh` pre-flight |
| fetch_failed | `hl7_file_input` rows with `parse_finished=0 AND retry_num=0` in the lookback window, plus their `quarantined_orders` rows (provider NPI, patient, OBR codes) | `triage_prompt.md` Step 1 |
| classify | A = `emr_code_not_found`; CNF = `customer_not_found`; B = `order_input` present; C = everything else | Step 2 (+ customer_not_found split out) |
| resolve_customer | ORC.12 NPI (order_input, else quarantine) -> `ehr_integrations` LIVE + ordering_enabled, FULL_INTEGRATION > ORDER_ONLY > other, newest `updated_at` wins. Non-NPI ORC.12 values are tried as `customer_id`. No NPI -> practice candidates by sftpDir, flagged ambiguous | Step 2.5, `emr-order-customer-resolution` skill, emr-v2 `resolveOrderingIntegration` |
| lookup_codes | per code, by prefix: VACP -> bundle mapping (`oldOrderTypeId`, custom bundles checked against the winning customer/clinic); VATEST -> package price TEST by `orderTypeId`; VAREQUISTION -> package price by lowercase `uniqueemrcode`; legacy aliases applied first; `isOrderable` gate | Step 3, emr-v2 `obr-parser.service.ts`, `order-mapping-cache.service.ts`, `order-legacy-code-mapper.service.ts` |
| write_report | tables from state + narrative from `claude -p` (structured output); falls back to the deterministic report if the LLM fails | Step 5 |
| send_mail | `../send_triage_mail.py` (shared SMTP transport with ticket_watch) | - |

## What the graph does NOT do

- **No prod writes.** Type B payment/order recovery (Step 4 of the prompt)
  places orders and charges cards; the graph only lists those rows as pending
  manual recovery. Keep using the prompt path or a reviewed script for that.
- No Jira, no Slack. Output is the markdown file and the email.

## Running

```bash
python3.13 -m venv ~/.venvs/hl7-triage-graph
~/.venvs/hl7-triage-graph/bin/pip install -r DailyJob/hl7_fail/graph/requirements.txt

cd DailyJob/hl7_fail/graph
~/.venvs/hl7-triage-graph/bin/python -m hl7_triage_graph --dry-run          # report, no mail
~/.venvs/hl7-triage-graph/bin/python -m hl7_triage_graph --no-llm --dry-run # deterministic only
~/.venvs/hl7-triage-graph/bin/python -m hl7_triage_graph --print-graph      # mermaid
```

`../run_graph.sh` is the launchd-shaped wrapper. With `PARALLEL=1` (default)
it writes to `DailyJob/hl7_fail/graph_out/` and does not mail, so it can run
beside the existing 04:00 job for comparison. Switch-over: point
`com.lis.hl7-triage` at `run_graph.sh` with `PARALLEL=0`.

Exit codes: 0 ok, 1 blocked (DB down / unconfigured), 4 LLM narrative failed
(deterministic report still written and mailed).

## Configuration (agent root `.env`, never committed)

```
LIS_EMR_DB_HOST=lisportalprod2.mysql.database.azure.com
LIS_EMR_DB_PORT=3306
LIS_EMR_DB_USER=lis_core_emr
LIS_EMR_DB_PASSWORD=...
LIS_EMR_DB_NAME=lis_emr
PRICING_API_TOKEN=Bearer ...        # optional; falls back to EMR-Backend orderApi.yaml orderApiToken.prod
HL7_TRIAGE_MODEL=fable              # optional; model passed to claude -p
REPORT_SMTP_HOST / REPORT_SMTP_PORT / REPORT_SMTP_USER / REPORT_SMTP_PASSWORD / REPORT_EMAIL_TO
```

The LLM node spawns `claude -p` with every `ANTHROPIC_*` variable removed
from its environment and an empty working directory. The machine's claude.ai
login is what authenticates it; no API key is needed or read. `.env` carries
`ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` for a different proxy, and letting
those reach `claude -p` breaks its login (ticket_watch, 2026-09-30).

## Layout

```
graph/
  requirements.txt
  hl7_triage_graph/
    config.py    .env + orderApi.yaml, paths, constants
    state.py     TriageState TypedDict
    db.py        read-only queries (hl7_file_input, quarantined_orders, ehr_integrations)
    resolve.py   customer resolution
    pricing.py   catalog download + per-code lookup
    llm.py       claude -p transport (stdin prompt, --json-schema, scrubbed env)
    report.py    markdown rendering
    nodes.py     node functions + narrative schema/instructions
    graph.py     wiring
    __main__.py  CLI
```
