#!/bin/bash
# Daily LIS-Sample route-removal check (runbooks/lis-sample-route-migration.md).
# From the first announced deadline on, measures traffic on every migrated
# route and opens a draft removal PR on LIS-Sample for the ones that meet the
# removal rule. It never merges and never deletes anything itself.
#
# Disarms itself when every route in routes.json is in state.json `handled`.
set -uo pipefail

REPO=/Users/hung.l/src/vibrant-america-working-agent
JOB_DIR="$REPO/DailyJob/lis_sample_route_removal"
LABEL=com.lis.lis-sample-route-removal
START_DATE=2026-10-31   # day after the first deadline (2026-10-30)

cd "$REPO" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export HOME=/Users/hung.l

notify() {
  osascript -e "display notification \"$1\" with title \"LIS-Sample route removal\"" 2>/dev/null
}

today=$(TZ=America/Los_Angeles date +%F)
if [[ "$today" < "$START_DATE" ]]; then
  echo "$(date -u +%FT%TZ) before $START_DATE; nothing to do"
  exit 0
fi

git pull -q --ff-only origin main || echo "note: pull failed; continuing on local main"

remaining=$(python3 - "$JOB_DIR" <<'EOF'
import json, os, sys
d = sys.argv[1]
routes = json.load(open(os.path.join(d, "routes.json")))["routes"]
p = os.path.join(d, "state.json")
handled = json.load(open(p)).get("handled", {}) if os.path.exists(p) else {}
print(sum(1 for r in routes if f"{r['method']} {r['path']}" not in handled))
EOF
)
if [ "$remaining" = "0" ]; then
  echo "$(date -u +%FT%TZ) every route handled; disarming"
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  exit 0
fi

echo "=== $(date -u +%FT%TZ) route-removal check, $remaining routes not yet handled ==="
REMOVAL_MODEL="${REMOVAL_MODEL:-opus}"
PROMPT="$(cat "$JOB_DIR/prompt.md")"

rc=1
for attempt in 1 2; do
  echo "--- claude attempt $attempt ---"
  caffeinate -i claude -p "$PROMPT" --model "$REMOVAL_MODEL" --dangerously-skip-permissions 2>&1
  rc=$?
  echo "--- claude exit code: $rc (attempt $attempt) ---"
  [ $rc -eq 0 ] && break
  sleep 60
done

if [ $rc -ne 0 ]; then
  notify "Check did NOT run - see DailyJob/lis_sample_route_removal/launchd_stdout.log"
  exit $rc
fi
exit 0
