#!/bin/bash
# HL7 triage - LangGraph runner (parallel-run phase).
#
# Writes DailyJob/hl7_fail/graph_out/triage_<date>.md and does NOT mail, so it
# can run next to the prompt-driven run_triage.sh for a week of side-by-side
# comparison. Switch-over = point com.lis.hl7-triage at this script and drop
# PARALLEL=1 (then the graph writes triage_<date>.md in place and mails it).
AGENT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GRAPH_DIR="${AGENT_ROOT}/DailyJob/hl7_fail/graph"
VENV="${HL7_TRIAGE_VENV:-$HOME/.venvs/hl7-triage-graph}"
PARALLEL="${PARALLEL:-1}"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export PYTHONPATH="${GRAPH_DIR}${PYTHONPATH:+:$PYTHONPATH}"

TODAY=$(date +%Y-%m-%d)
LOG_FILE="${AGENT_ROOT}/DailyJob/hl7_fail/graph_run_${TODAY}.log"

if [[ ! -x "${VENV}/bin/python" ]]; then
    echo "[$(date)] venv missing at ${VENV}; create with: python3.13 -m venv ${VENV} && ${VENV}/bin/pip install -r ${GRAPH_DIR}/requirements.txt" >> "$LOG_FILE"
    exit 2
fi

ARGS=(--date "$TODAY")
if [[ "$PARALLEL" == "1" ]]; then
    ARGS+=(--out-dir "${AGENT_ROOT}/DailyJob/hl7_fail/graph_out" --dry-run)
fi

echo "=== hl7_triage_graph start $(date) (parallel=${PARALLEL}) ===" >> "$LOG_FILE"
"${VENV}/bin/python" -m hl7_triage_graph "${ARGS[@]}" "$@" >> "$LOG_FILE" 2>&1
RC=$?
echo "=== hl7_triage_graph exit ${RC} $(date) ===" >> "$LOG_FILE"
exit $RC
