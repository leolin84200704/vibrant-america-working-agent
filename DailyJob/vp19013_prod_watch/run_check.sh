#!/bin/bash
# VP-19013 prod watch: verify the Foundation Zoomer / Foundation Baseline
# male (PSA) swap on the first real male EMR order after the 2026-11-09 release.
# Read-only. Disarms itself once state.json says done, or after END_DATE.
set -uo pipefail

REPO=/Users/hung.l/src/vibrant-america-working-agent
JOB_DIR="$REPO/DailyJob/vp19013_prod_watch"
LABEL=com.lis.vp19013-prod-watch
START_DATE=2026-11-09   # release: Mon 11/09 00:00 ET
END_DATE=2026-12-09     # give up after 30 days and report

cd "$REPO" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export HOME=/Users/hung.l

notify() {
  osascript -e "display notification \"$1\" with title \"VP-19013 prod watch\"" 2>/dev/null
}

disarm() {
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
}

today=$(TZ=America/Los_Angeles date +%F)
if [[ "$today" < "$START_DATE" ]]; then
  echo "$(date -u +%FT%TZ) before $START_DATE; nothing to do"
  exit 0
fi

git pull -q --ff-only origin main || echo "note: pull failed; continuing on local main"

status=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('status','watching'))" "$JOB_DIR/state.json" 2>/dev/null || echo watching)
if [ "$status" = "done" ]; then
  echo "$(date -u +%FT%TZ) state is done; disarming"
  disarm
  exit 0
fi

FINAL=0
[[ "$today" > "$END_DATE" ]] && FINAL=1

echo "=== $(date -u +%FT%TZ) VP-19013 prod watch (final=$FINAL) ==="
WATCH_MODEL="${WATCH_MODEL:-opus}"
PROMPT="$(cat "$JOB_DIR/prompt.md")

FINAL_RUN=$FINAL  (1 = the 30-day window is over: write the final report, set state to done.)"

rc=1
for attempt in 1 2; do
  echo "--- claude attempt $attempt ---"
  caffeinate -i claude -p "$PROMPT" --model "$WATCH_MODEL" --dangerously-skip-permissions 2>&1
  rc=$?
  echo "--- claude exit code: $rc (attempt $attempt) ---"
  [ $rc -eq 0 ] && break
  sleep 60
done

if [ $rc -ne 0 ]; then
  notify "Check did NOT run - see DailyJob/vp19013_prod_watch/launchd_stdout.log"
  exit $rc
fi
[ $FINAL -eq 1 ] && disarm
exit 0
