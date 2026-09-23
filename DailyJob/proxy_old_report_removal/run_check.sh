#!/bin/bash
# VP-18324 one-shot: on 2026-09-30 the removal notice for
# /proxy/old-report/downloadTestOrderPDF expires. This checks the traffic and,
# only if it is genuinely zero, prepares a ticket and a draft PR for Leo.
#
# It never removes anything itself, and it never merges.
#
# One-shot semantics: launchd's StartCalendarInterval with a Month+Day fires
# again next year, so the job disarms itself two ways — a done-marker checked on
# entry, and a launchctl bootout after a completed run. The marker is the one
# that matters; the bootout is best-effort and may fail if the agent was loaded
# under a different domain.
set -uo pipefail

REPO=/Users/hung.l/src/vibrant-america-working-agent
JOB_DIR="$REPO/DailyJob/proxy_old_report_removal"
MARKER="$JOB_DIR/.done"
LABEL=com.lis.proxy-old-report-removal

cd "$REPO" || exit 1

# launchd gives a minimal PATH; brew tools (claude, gh, git) must resolve.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export HOME=/Users/hung.l

notify() {
  osascript -e "display notification \"$1\" with title \"VP-18324 proxy removal\"" 2>/dev/null
}

if [ -f "$MARKER" ]; then
  echo "$(date -u +%FT%TZ) already ran on $(cat "$MARKER") — nothing to do"
  exit 0
fi

echo "=== $(date -u +%FT%TZ) VP-18324 removal check starting ==="
echo "claude=$(command -v claude)  gh=$(command -v gh)  git=$(command -v git)"

# Pin the model. An unpinned `claude -p` can change under us between the day
# this was written and the day it fires, which for a job that opens a PR is not
# a difference worth discovering in production.
REMOVAL_MODEL="${REMOVAL_MODEL:-fable}"

PROMPT="$(cat "$JOB_DIR/prompt.md")"

rc=1
for attempt in 1 2; do
  echo "--- claude attempt $attempt ---"
  caffeinate -i claude -p "$PROMPT" --model "$REMOVAL_MODEL" --dangerously-skip-permissions 2>&1
  rc=$?
  echo "--- claude exit code: $rc (attempt $attempt) ---"
  [ $rc -eq 0 ] && break
  echo "claude failed; retrying in 60s..."
  sleep 60
done

if [ $rc -ne 0 ]; then
  # Do NOT write the marker: a run that never happened must fire again rather
  # than silently disarm itself. Leo gets told either way.
  echo "$(date -u +%FT%TZ) run failed after 2 attempts; leaving the job armed"
  notify "Check did NOT run — see DailyJob/proxy_old_report_removal/launchd_stderr.log"
  exit $rc
fi

date -u +%FT%TZ > "$MARKER"
echo "$(date -u +%FT%TZ) completed; marker written"

# Best-effort disarm so this does not fire again next September.
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null \
  || launchctl unload "$HOME/Library/LaunchAgents/$LABEL.plist" 2>/dev/null \
  || echo "note: could not unload $LABEL; the done-marker still prevents a re-run"

notify "Check complete — see DailyJob/proxy_old_report_removal/ for the report"
exit 0
