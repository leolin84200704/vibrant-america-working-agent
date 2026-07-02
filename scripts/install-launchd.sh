#!/bin/bash
# Generate + install the launchd jobs (dream nightly 18:30, weekly Sunday 11:00)
# for THIS machine's checkout path. The old committed plists hardcoded
# /Users/hung.l/src/lis-code-agent, so on any other machine the jobs silently
# never existed — that is how the dream pipeline died without anyone noticing.
#
# Usage: bash scripts/install-launchd.sh          # install/refresh both jobs
#        bash scripts/install-launchd.sh --status # show current state
set -euo pipefail

AGENT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCH_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_DIR" "$AGENT_ROOT/logs"

if [[ "${1:-}" == "--status" ]]; then
    for label in com.lis-code-agent.dream com.lis-code-agent.weekly; do
        echo "== $label =="
        launchctl list "$label" 2>/dev/null || echo "  not loaded"
    done
    exit 0
fi

make_plist() {
    local label="$1" script="$2" calendar="$3" out="$LAUNCH_DIR/$1.plist"
    cat > "$out" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$label</string>
    <key>ProgramArguments</key>
    <array>
        <string>$AGENT_ROOT/scripts/$script</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
$calendar
    </dict>
    <key>StandardOutPath</key>
    <string>$AGENT_ROOT/logs/launchd-$label-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$AGENT_ROOT/logs/launchd-$label-stderr.log</string>
    <key>WorkingDirectory</key>
    <string>$AGENT_ROOT</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
EOF
    launchctl unload "$out" 2>/dev/null || true
    launchctl load "$out"
    echo "installed + loaded: $out -> $AGENT_ROOT/scripts/$script"
}

make_plist com.lis-code-agent.dream run-dream.sh \
"        <key>Hour</key>
        <integer>18</integer>
        <key>Minute</key>
        <integer>30</integer>"

make_plist com.lis-code-agent.weekly weekly-routine.sh \
"        <key>Weekday</key>
        <integer>0</integer>
        <key>Hour</key>
        <integer>11</integer>
        <key>Minute</key>
        <integer>0</integer>"

echo
echo "Verify: launchctl list | grep lis-code-agent"
