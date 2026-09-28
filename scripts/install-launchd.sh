#!/bin/bash
# Generate + install the launchd jobs (dream 08:15/12:30/18:30/21:30, weekly Sunday 11:00)
# for THIS machine's checkout path. The old committed plists hardcoded
# /Users/hung.l/src/vibrant-america-working-agent, so on any other machine the jobs silently
# never existed — that is how the dream pipeline died without anyone noticing.
#
# Usage: bash scripts/install-launchd.sh               # install/refresh both jobs
#        bash scripts/install-launchd.sh --status      # show current state
#        bash scripts/install-launchd.sh dream         # only the dream job
#        bash scripts/install-launchd.sh --render-only DIR
#            write the plists to DIR and run no launchctl at all.
#
# The job selector defaults to `all` for compatibility, but note that `all` LOADS
# the weekly job, which on Leo's machine has never been loaded. Use `dream` to
# refresh the nightly job without deciding that question by accident.
#
# --render-only exists because there is no other safe way to look at what this
# script produces. `launchctl load` addresses jobs by the Label inside the file,
# not by where the file lives, so running the installer with a redirected HOME
# still rebinds the REAL job — on 2026-09-28 a review of the generated plist did
# exactly that, repointed the live dream job at a worktree checkout, and loaded a
# weekly job that had deliberately never been loaded.
set -euo pipefail

AGENT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCH_DIR="$HOME/Library/LaunchAgents"
RENDER_ONLY=0
if [[ "${1:-}" == "--render-only" ]]; then
    RENDER_ONLY=1
    LAUNCH_DIR="${2:?--render-only needs a target directory}"
    shift 2
fi
JOB="${1:-all}"
case "$JOB" in
    --status) ;;  # not a job selector; handled by the block below, which exits
    all|dream|weekly) ;;
    *) echo "unknown job '$JOB' (expected: all, dream, weekly)" >&2; exit 2 ;;
esac
mkdir -p "$LAUNCH_DIR" "$AGENT_ROOT/logs"

if [[ "${1:-}" == "--status" ]]; then
    for label in com.vibrant-america-working-agent.dream com.vibrant-america-working-agent.weekly; do
        echo "== $label =="
        launchctl list "$label" 2>/dev/null || echo "  not loaded"
    done
    exit 0
fi

# $3 is the rendered <key>StartCalendarInterval</key> block — a single <dict> for a
# job that runs once, an <array> of <dict>s for one that gets several chances a day.
# $4/$5 are the stdout/stderr paths, kept as a parameter so the dream job can keep
# writing the log filenames its history is already under.
make_plist() {
    local label="$1" script="$2" calendar="$3" out="$LAUNCH_DIR/$1.plist"
    local outlog="${4:-$AGENT_ROOT/logs/launchd-$1-stdout.log}"
    local errlog="${5:-$AGENT_ROOT/logs/launchd-$1-stderr.log}"
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
$calendar
    <key>StandardOutPath</key>
    <string>$outlog</string>
    <key>StandardErrorPath</key>
    <string>$errlog</string>
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
    if [[ $RENDER_ONLY -eq 1 ]]; then
        echo "rendered (not loaded): $out"
        return
    fi
    launchctl unload "$out" 2>/dev/null || true
    launchctl load "$out"
    echo "installed + loaded: $out -> $AGENT_ROOT/scripts/$script"
}

# Four firings, not one. 18:30 is still the intended time, but a MacBook is often
# asleep then (2026-09-25..27: three nights running fired into DarkWake, found no
# DNS and recorded the night as failed), and launchd's catch-up on wake lands in the
# same dead window. The extra times are when the lid is demonstrably open. run-dream.sh
# skips any firing that a successful run has already covered, so at most one of the
# four does work on a given day and the rest cost a subshell.
DREAM_TIMES="    <key>StartCalendarInterval</key>
    <array>"
for hhmm in 08:15 12:30 18:30 21:30; do
    DREAM_TIMES="$DREAM_TIMES
        <dict>
            <key>Hour</key>
            <integer>${hhmm%%:*}</integer>
            <key>Minute</key>
            <integer>${hhmm##*:}</integer>
        </dict>"
done
DREAM_TIMES="$DREAM_TIMES
    </array>"

[[ "$JOB" == "all" || "$JOB" == "dream" ]] && \
make_plist com.vibrant-america-working-agent.dream run-dream.sh "$DREAM_TIMES" \
    "$AGENT_ROOT/logs/launchd-stdout.log" "$AGENT_ROOT/logs/launchd-stderr.log"

[[ "$JOB" == "all" || "$JOB" == "weekly" ]] && \
make_plist com.vibrant-america-working-agent.weekly weekly-routine.sh \
"        <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>0</integer>
        <key>Hour</key>
        <integer>11</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>"

echo
echo "Verify: launchctl list | grep vibrant-america-working-agent"
