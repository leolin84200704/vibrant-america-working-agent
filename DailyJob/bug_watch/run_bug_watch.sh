#!/bin/bash
# AI-native bug watch — scheduled triage of newly created bug tickets.
# Runs via launchd twice daily (com.lis.bug-watch.plist):
#   11:30 -> look back 17h (covers overnight, since yesterday 18:30)
#   17:30 -> look back 7h  (covers the workday, since 10:30)
# Install: cp DailyJob/bug_watch/com.lis.bug-watch.plist ~/Library/LaunchAgents/ \
#          && launchctl load ~/Library/LaunchAgents/com.lis.bug-watch.plist

AGENT_ROOT="/Users/hung.l/src/vibrant-america-working-agent"
WATCH_DIR="${AGENT_ROOT}/DailyJob/bug_watch"
PROMPT_FILE="${WATCH_DIR}/watch_prompt.md"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# Which run is this? Before 14:00 = morning run (17h lookback), else evening (7h).
HOUR=$(date +%H)
if [[ $HOUR -lt 14 ]]; then
    RUN_TAG="am"; LOOKBACK_HOURS=17
else
    RUN_TAG="pm"; LOOKBACK_HOURS=7
fi

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
    SUMMARY=$(grep -m1 '^- Total' "$REPORT_FILE" 2>/dev/null || echo "report ready")
    osascript -e "display notification \"${SUMMARY}\" with title \"Bug Watch (${RUN_TAG})\"" >/dev/null 2>&1 || true
else
    osascript -e 'display notification "Bug watch run failed — check log" with title "Bug Watch" sound name "Basso"' >/dev/null 2>&1 || true
    exit 1
fi
