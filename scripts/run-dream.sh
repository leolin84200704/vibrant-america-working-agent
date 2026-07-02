#!/bin/bash
set -uo pipefail

AGENT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$AGENT_ROOT"

DATE=$(date +%Y-%m-%d)
LOG_DIR="$AGENT_ROOT/logs"
mkdir -p "$LOG_DIR"

if [[ "${1:-}" == "--dry" ]]; then
    echo "DRY RUN: would execute dream pipeline"
    echo "  Agent root: $AGENT_ROOT"
    echo "  Date: $DATE"
    echo "  Command: claude -p \"\$(cat scripts/dream.md)\" --allowedTools Read,Write,Edit,Glob,Grep,Bash"
    exit 0
fi

LOG_FILE="$LOG_DIR/launchd-stdout-$DATE.log"

echo "[$(date)] Starting dream pipeline..." | tee -a "$LOG_FILE"
echo "  Agent root: $AGENT_ROOT" | tee -a "$LOG_FILE"

# A missing claude binary must fail loudly — previously it produced no dream
# log and no notification (output had no "API Error" so it looked like success).
if ! command -v claude >/dev/null 2>&1; then
    echo "[$(date)] FATAL: claude CLI not found on PATH ($PATH)" | tee -a "$LOG_FILE"
    osascript -e 'display notification "claude CLI not found — dream pipeline cannot run" with title "LIS Code Agent" sound name "Basso"' >/dev/null 2>&1 || true
    exit 1
fi

# Wait up to 60s for network (just woken from sleep may need a moment)
for i in $(seq 1 30); do
    if curl -sS --max-time 3 -o /dev/null https://api.anthropic.com/; then
        echo "[$(date)] Network ready (attempt $i)" | tee -a "$LOG_FILE"
        break
    fi
    sleep 2
done

PROMPT=$(cat scripts/dream.md)
ATTEMPT=1
MAX_ATTEMPTS=3
SUCCESS=0

while [[ $ATTEMPT -le $MAX_ATTEMPTS ]]; do
    echo "[$(date)] === Dream attempt $ATTEMPT/$MAX_ATTEMPTS ===" | tee -a "$LOG_FILE"
    TMP=$(mktemp)
    claude -p "$PROMPT" \
        --allowedTools "Read,Write,Edit,Glob,Grep,Bash" \
        > "$TMP" 2>&1
    CLAUDE_EXIT=$?
    cat "$TMP" | tee -a "$LOG_FILE"

    # Success requires BOTH zero exit and no API error — grepping alone let
    # hard failures (crash, command error) pass as success.
    if [[ $CLAUDE_EXIT -eq 0 ]] && ! grep -q "API Error" "$TMP"; then
        SUCCESS=1
        rm -f "$TMP"
        break
    fi
    rm -f "$TMP"

    if [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; then
        echo "[$(date)] Attempt $ATTEMPT hit API error, retrying in 30s..." | tee -a "$LOG_FILE"
        sleep 30
    fi
    ATTEMPT=$((ATTEMPT + 1))
done

if [[ $SUCCESS -eq 0 ]]; then
    echo "[$(date)] FAILED after $MAX_ATTEMPTS attempts" | tee -a "$LOG_FILE"
    osascript -e 'display notification "Dream pipeline failed after retries" with title "LIS Code Agent" sound name "Basso"' >/dev/null 2>&1 || true
    exit 1
fi

# Post-dream: refresh failure index + snapshot evaluation metrics.
# Both are idempotent. Failures here are logged but do not fail the pipeline.
echo "[$(date)] Post-dream: refresh failure index" | tee -a "$LOG_FILE"
if ! python3 scripts/extract-failures.py 2>&1 | tee -a "$LOG_FILE"; then
    echo "[$(date)] WARN: extract-failures.py failed (non-fatal)" | tee -a "$LOG_FILE"
fi

echo "[$(date)] Post-dream: capture eval snapshot dream-$DATE" | tee -a "$LOG_FILE"
if ! python3 scripts/eval.py --label "dream-$DATE" 2>&1 | tail -30 | tee -a "$LOG_FILE"; then
    echo "[$(date)] WARN: eval.py failed (non-fatal)" | tee -a "$LOG_FILE"
fi

echo "[$(date)] Dream pipeline complete. Log: $LOG_FILE" | tee -a "$LOG_FILE"
