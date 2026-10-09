#!/bin/bash
# Reply assistant - launchd entry (com.lis.slack-assist): every 20 min, Mon-Fri 09:00-18:00.
# The window is enforced inside assist_poll.py as well, so a stray fire outside it costs nothing.
AGENT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ASSIST_DIR="${AGENT_ROOT}/DailyJob/slack_assist"
VENV="${ASSIST_VENV:-$HOME/.venvs/slack-assist}"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export CLAUDE_CODE_DISABLE_AUTO_MEMORY=1
LOG="${ASSIST_DIR}/launchd_$(date +%Y-%m-%d).log"
if [[ ! -x "${VENV}/bin/python" ]]; then
    echo "[$(date)] venv missing: python3.13 -m venv ${VENV} && ${VENV}/bin/pip install -r ${ASSIST_DIR}/requirements.txt" >> "$LOG"
    exit 2
fi
"${VENV}/bin/python" "${ASSIST_DIR}/assist_poll.py" "$@" >> "$LOG" 2>&1
exit $?
