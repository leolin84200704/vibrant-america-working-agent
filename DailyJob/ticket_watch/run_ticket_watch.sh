#!/bin/bash
# Ticket Watch — morning analysis run (Phase 1: read-only).
# Scheduled via launchd at 08:00 (com.lis.ticket-watch.plist). Scans Leo's Jira
# queue, analyzes each ticket per WORK-LOOP Step 1-2, and writes
# DailyJob/ticket_watch/report_YYYY-MM-DD.md. A second job (com.lis.ticket-report-mail,
# 09:00) emails that file; this script never sends anything itself.
#
# Lookback is dynamic: hours since the newest previous report (+1h overlap),
# clamped to [24, 168]h, so days missed while the Mac slept are swept up on wake.
#
# Install: cp DailyJob/ticket_watch/com.lis.ticket-watch.plist ~/Library/LaunchAgents/ \
#          && launchctl load ~/Library/LaunchAgents/com.lis.ticket-watch.plist

# Overridable so a trial run can target a worktree checkout (with its own .env link)
# instead of the live main checkout.
AGENT_ROOT="${TICKETWATCH_AGENT_ROOT:-/Users/hung.l/src/vibrant-america-working-agent}"
WATCH_DIR="${AGENT_ROOT}/DailyJob/ticket_watch"
PROMPT_FILE="${WATCH_DIR}/watch_prompt.md"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# Headless runs must not touch Claude Code's native auto memory (the agent repo is
# the system of record), and must pin the model — an unpinned `claude -p` inherits
# the interactive default and silently bills it every morning.
export CLAUDE_CODE_DISABLE_AUTO_MEMORY=1
TICKETWATCH_MODEL="${TICKETWATCH_MODEL:-fable}"

TODAY=$(date +%Y-%m-%d)
LOG_FILE="${WATCH_DIR}/run_${TODAY}.log"
REPORT_FILE="${WATCH_DIR}/report_${TODAY}.md"
mkdir -p "$WATCH_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"; }

# A report that says WHY there is nothing to read beats no report: the 09:00 mailer
# sends whatever file exists, so every early exit below leaves one behind.
write_failure_report() {
    cat > "$REPORT_FILE" <<REPORT
# Ticket Watch — ${TODAY} — RUN FAILED

## Summary
- (run failed before any ticket was analyzed)

**$1**

Log: ${LOG_FILE}
REPORT
}

# Dynamic lookback from the newest previous report (not today's, if a rerun).
LAST_REPORT=$(ls -t "${WATCH_DIR}"/report_*.md 2>/dev/null | grep -v "report_${TODAY}.md" | head -1)
if [[ -n "$LAST_REPORT" ]]; then
    LAST_TS=$(stat -f %m "$LAST_REPORT")
    LOOKBACK_HOURS=$(( ($(date +%s) - LAST_TS) / 3600 + 1 ))
else
    LOOKBACK_HOURS=24
fi
[[ $LOOKBACK_HOURS -lt 24 ]] && LOOKBACK_HOURS=24
[[ $LOOKBACK_HOURS -gt 168 ]] && LOOKBACK_HOURS=168

# Wait up to 60s for network (the Mac may have just woken).
NET_OK=0
for i in $(seq 1 30); do
    if curl -sS --max-time 3 -o /dev/null https://api.anthropic.com/; then NET_OK=1; break; fi
    sleep 2
done
if [[ $NET_OK -eq 0 ]]; then
    log "Network unavailable after 60s — aborting"
    write_failure_report "No network: api.anthropic.com unreachable for 60s, nothing was scanned."
    exit 1
fi

# Jira pre-flight with the same credentials the prompt will use. A dead Jira is
# reported as such, never as an empty queue.
# Read ONLY the three Jira values. Sourcing the whole .env with `set -a` exported its
# empty ANTHROPIC_API_KEY= / ANTHROPIC_BASE_URL= lines into claude -p, which then
# skipped the keychain login and failed with "401 Authentication Failed" (trial run
# 2026-09-30). Nothing from .env may leak into the claude process environment.
env_value() { grep -m1 "^$1=" "${AGENT_ROOT}/.env" 2>/dev/null | cut -d= -f2- | tr -d "\"'"; }
JIRA_SERVER=$(env_value JIRA_SERVER); JIRA_EMAIL=$(env_value JIRA_EMAIL); JIRA_API_TOKEN=$(env_value JIRA_API_TOKEN)
JIRA_HTTP=$(curl -sS --max-time 15 -o /dev/null -w '%{http_code}' \
    -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" "${JIRA_SERVER}/rest/api/3/myself" 2>/dev/null || echo 000)
if [[ "$JIRA_HTTP" != "200" ]]; then
    log "Jira pre-flight failed: HTTP ${JIRA_HTTP} on /rest/api/3/myself"
    write_failure_report "JIRA UNREACHABLE: /rest/api/3/myself returned HTTP ${JIRA_HTTP}. Check whether JIRA_API_TOKEN in .env has expired."
    exit 1
fi

# Prod DB is optional in Phase 1 (only bug diagnoses need it); tell the prompt
# what it can expect rather than skipping the run like bug_watch does.
DB_HOST="lisportalprod2.mysql.database.azure.com"
if nc -z -w 5 "$DB_HOST" 3306 >/dev/null 2>&1; then DB_STATUS="up"; else DB_STATUS="down"; fi

log "Run start lookback=${LOOKBACK_HOURS}h jira=OK db=${DB_STATUS} model=${TICKETWATCH_MODEL}"

PROMPT=$(sed -e "s/{{LOOKBACK_HOURS}}/${LOOKBACK_HOURS}/g" \
             -e "s|{{REPORT_FILE}}|${REPORT_FILE}|g" \
             -e "s/{{DB_STATUS}}/${DB_STATUS}/g" "$PROMPT_FILE")

ATTEMPT=1; MAX_ATTEMPTS=2; SUCCESS=0
while [[ $ATTEMPT -le $MAX_ATTEMPTS ]]; do
    log "=== attempt ${ATTEMPT}/${MAX_ATTEMPTS} ==="
    TMP=$(mktemp)
    # Phase 1 tool set: Write is needed for the report file; the prompt forbids every
    # other write. Edit is deliberately absent so nothing existing can be modified.
    ( cd "$AGENT_ROOT" && claude -p "$PROMPT" \
        --model "$TICKETWATCH_MODEL" \
        --allowedTools "Bash,Read,Grep,Glob,Write,Agent" \
        --max-turns 150 ) > "$TMP" 2>&1
    cat "$TMP" >> "$LOG_FILE"
    log "=== attempt ${ATTEMPT} finished ==="
    if ! grep -q "API Error" "$TMP"; then SUCCESS=1; rm -f "$TMP"; break; fi
    rm -f "$TMP"
    [[ $ATTEMPT -lt $MAX_ATTEMPTS ]] && sleep 30
    ATTEMPT=$((ATTEMPT + 1))
done

if [[ $SUCCESS -eq 1 && -f "$REPORT_FILE" ]]; then
    SUMMARY=$(grep -A1 -m1 '^## Summary' "$REPORT_FILE" 2>/dev/null | tail -1 || echo "report written")
    log "OK: ${SUMMARY}"
    osascript -e "display notification \"${SUMMARY}\" with title \"Ticket Watch ${TODAY}\"" >/dev/null 2>&1 || true
    exit 0
fi

log "FAILED: success=${SUCCESS} report_exists=$([[ -f "$REPORT_FILE" ]] && echo yes || echo no)"
[[ -f "$REPORT_FILE" ]] || write_failure_report "claude -p finished without producing a report (or hit API Error twice)."
osascript -e 'display notification "Ticket watch run failed — check log" with title "Ticket Watch" sound name "Basso"' >/dev/null 2>&1 || true
exit 1
