#!/bin/bash
# Ticket Watch — 09:00 mailer. Sends DailyJob/ticket_watch/report_<today>.md to Leo,
# or an explicit "no report was produced" alert when the 08:00 run left nothing.
# Deterministic shell + python only; no LLM call.
AGENT_ROOT="/Users/hung.l/src/vibrant-america-working-agent"
WATCH_DIR="${AGENT_ROOT}/DailyJob/ticket_watch"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

TODAY=$(date +%Y-%m-%d)
LOG_FILE="${WATCH_DIR}/run_${TODAY}.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] mailer start" >> "$LOG_FILE"
python3 "${WATCH_DIR}/send_report.py" --date "$TODAY" >> "$LOG_FILE" 2>&1
RC=$?
echo "[$(date '+%Y-%m-%d %H:%M:%S')] mailer exit=${RC}" >> "$LOG_FILE"
exit $RC
