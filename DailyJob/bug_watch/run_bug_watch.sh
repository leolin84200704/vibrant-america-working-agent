#!/bin/bash
# AI-native bug watch — scheduled triage of newly created bug tickets.
# Runs via launchd every 2 hours (com.lis.bug-watch.plist, odd hours at :30).
# Lookback is dynamic: covers everything since the newest previous watch
# report (+1h overlap for dedupe), clamped to [3, 24]h — so runs missed
# while the Mac sleeps are caught up in one sweep on wake.
# Install: cp DailyJob/bug_watch/com.lis.bug-watch.plist ~/Library/LaunchAgents/ \
#          && launchctl load ~/Library/LaunchAgents/com.lis.bug-watch.plist

AGENT_ROOT="/Users/hung.l/src/vibrant-america-working-agent"
WATCH_DIR="${AGENT_ROOT}/DailyJob/bug_watch"
PROMPT_FILE="${WATCH_DIR}/watch_prompt.md"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# Dynamic lookback: hours since the newest previous report, +1h overlap.
LAST_REPORT=$(ls -t "${WATCH_DIR}"/watch_*.md 2>/dev/null | head -1)
if [[ -n "$LAST_REPORT" ]]; then
    LAST_TS=$(stat -f %m "$LAST_REPORT")
    NOW_TS=$(date +%s)
    LOOKBACK_HOURS=$(( (NOW_TS - LAST_TS) / 3600 + 1 ))
else
    LOOKBACK_HOURS=17
fi
[[ $LOOKBACK_HOURS -lt 3 ]] && LOOKBACK_HOURS=3
[[ $LOOKBACK_HOURS -gt 24 ]] && LOOKBACK_HOURS=24

RUN_TAG=$(date +%H%M)
LOG_FILE="${WATCH_DIR}/run_$(date +%Y-%m-%d)_${RUN_TAG}.log"
REPORT_FILE="${WATCH_DIR}/watch_$(date +%Y-%m-%d)_${RUN_TAG}.md"

# Wait up to 60s for network
for i in $(seq 1 30); do
    if curl -sS --max-time 3 -o /dev/null https://api.anthropic.com/; then
        echo "[$(date)] Network ready (attempt $i)" >> "$LOG_FILE"
        break
    fi
    sleep 2
done

# Soft VPN/DB pre-flight: Jira (443) works either way, so the watch still runs;
# the prompt downgrades DB-dependent diagnosis to BLOCKED when DB_STATUS=down.
# Same Cisco CLI cautions as DailyJob/hl7_fail/run_triage.sh: parse only the
# LAST state line; `vpn connect` tears down a live session, so only attempt
# when unambiguously Disconnected.
DB_HOST="lisportalprod2.mysql.database.azure.com"
VPN_CLI="/opt/cisco/secureclient/bin/vpn"
VPN_SERVER="45.24.217.146"
db_reachable() { nc -z -w 5 "$DB_HOST" 3306 >/dev/null 2>&1; }

if ! db_reachable && [[ -x "$VPN_CLI" ]]; then
    VPN_STATE=$("$VPN_CLI" state 2>/dev/null | grep '>> state:' | tail -1 | awk '{print $NF}')
    echo "[$(date)] DB unreachable; Cisco state: ${VPN_STATE:-unknown}" >> "$LOG_FILE"
    if [[ "$VPN_STATE" == "Disconnected" ]]; then
        "$VPN_CLI" -s connect "$VPN_SERVER" < /dev/null >> "$LOG_FILE" 2>&1
        for i in $(seq 1 12); do db_reachable && break; sleep 5; done
    fi
fi
if db_reachable; then DB_STATUS="up"; else DB_STATUS="down"; fi
echo "[$(date)] Run=${RUN_TAG} lookback=${LOOKBACK_HOURS}h DB=${DB_STATUS}" >> "$LOG_FILE"

PROMPT=$(sed -e "s/{{LOOKBACK_HOURS}}/${LOOKBACK_HOURS}/g" \
             -e "s/{{DB_STATUS}}/${DB_STATUS}/g" \
             -e "s|{{REPORT_FILE}}|${REPORT_FILE}|g" "$PROMPT_FILE")

ATTEMPT=1
MAX_ATTEMPTS=2
SUCCESS=0
while [[ $ATTEMPT -le $MAX_ATTEMPTS ]]; do
    echo "=== Bug watch attempt $ATTEMPT/$MAX_ATTEMPTS started at $(date) ===" >> "$LOG_FILE"
    TMP=$(mktemp)
    cd "$AGENT_ROOT" && claude -p "$PROMPT" \
        --allowedTools "Bash,Read,Write,Edit,Grep,Glob" \
        --max-turns 80 \
        > "$TMP" 2>&1
    cat "$TMP" >> "$LOG_FILE"
    echo "=== Bug watch attempt $ATTEMPT finished at $(date) ===" >> "$LOG_FILE"
    if ! grep -q "API Error" "$TMP"; then
        SUCCESS=1; rm "$TMP"; break
    fi
    rm "$TMP"
    [[ $ATTEMPT -lt $MAX_ATTEMPTS ]] && sleep 30
    ATTEMPT=$((ATTEMPT + 1))
done

if [[ $SUCCESS -eq 1 && -f "$REPORT_FILE" ]]; then
    # With 12 runs/day, only notify when there is actually something new.
    SUMMARY=$(grep -m1 '^- Total' "$REPORT_FILE" 2>/dev/null || echo "")
    NEW_COUNT=$(echo "$SUMMARY" | grep -o 'Total new: [0-9]*' | grep -o '[0-9]*$')
    if [[ -n "$NEW_COUNT" && "$NEW_COUNT" -gt 0 ]]; then
        osascript -e "display notification \"${SUMMARY}\" with title \"Bug Watch (${RUN_TAG})\"" >/dev/null 2>&1 || true
    fi
else
    osascript -e 'display notification "Bug watch run failed — check log" with title "Bug Watch" sound name "Basso"' >/dev/null 2>&1 || true
    exit 1
fi
