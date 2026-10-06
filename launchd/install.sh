#!/bin/bash

set -e

PROJECT_DIR="$(
    cd "$(dirname "$0")/.."
    pwd
)"

PYTHON="$PROJECT_DIR/.venv/bin/python"
USER_ID="$(id -u)"

PLIST_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/.gitsync/logs"

WEB_LABEL="com.local.gitsync.web"
RUNNER_LABEL="com.local.gitsync.runner"

WEB_PLIST="$PLIST_DIR/$WEB_LABEL.plist"
RUNNER_PLIST="$PLIST_DIR/$RUNNER_LABEL.plist"

mkdir -p "$PLIST_DIR"
mkdir -p "$LOG_DIR"

if [ ! -x "$PYTHON" ]; then
    echo "Python environment not found:"
    echo "$PYTHON"
    exit 1
fi

PROJECT_DIR="$PROJECT_DIR" \
PYTHON="$PYTHON" \
HOME_DIR="$HOME" \
WEB_PLIST="$WEB_PLIST" \
RUNNER_PLIST="$RUNNER_PLIST" \
LOG_DIR="$LOG_DIR" \
"$PYTHON" <<'PY'
import os
import plistlib

project = os.environ["PROJECT_DIR"]
python = os.environ["PYTHON"]
home = os.environ["HOME_DIR"]
web_plist = os.environ["WEB_PLIST"]
runner_plist = os.environ["RUNNER_PLIST"]
log_dir = os.environ["LOG_DIR"]

path_env = (
    "/opt/homebrew/bin:"
    "/usr/local/bin:"
    "/usr/bin:"
    "/bin:"
    "/usr/sbin:"
    "/sbin"
)

env = {
    "HOME": home,
    "PATH": path_env,
    "PYTHONUNBUFFERED": "1",
}

web = {
    "Label": "com.local.gitsync.web",

    "ProgramArguments": [
        python,
        "-m",
        "uvicorn",
        "app:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8765",
    ],

    "WorkingDirectory": project,

    "RunAtLoad": True,
    "KeepAlive": True,

    "EnvironmentVariables": env,

    "StandardOutPath":
        f"{log_dir}/web.out.log",

    "StandardErrorPath":
        f"{log_dir}/web.err.log",
}

runner = {
    "Label": "com.local.gitsync.runner",

    "ProgramArguments": [
        python,
        f"{project}/runner.py",
    ],

    "WorkingDirectory": project,

    "StartCalendarInterval": [
        {
            "Weekday": weekday,
            "Hour": 10,
            "Minute": 30,
        }
        for weekday in range(1, 6)
    ],

    "EnvironmentVariables": env,

    "StandardOutPath":
        f"{log_dir}/runner.out.log",

    "StandardErrorPath":
        f"{log_dir}/runner.err.log",
}

with open(web_plist, "wb") as f:
    plistlib.dump(web, f)

with open(runner_plist, "wb") as f:
    plistlib.dump(runner, f)

print("Created:")
print(web_plist)
print(runner_plist)
PY

launchctl bootout \
    "gui/$USER_ID/$WEB_LABEL" \
    2>/dev/null || true

launchctl bootout \
    "gui/$USER_ID/$RUNNER_LABEL" \
    2>/dev/null || true

launchctl bootstrap \
    "gui/$USER_ID" \
    "$WEB_PLIST"

launchctl bootstrap \
    "gui/$USER_ID" \
    "$RUNNER_PLIST"

launchctl enable \
    "gui/$USER_ID/$WEB_LABEL"

launchctl enable \
    "gui/$USER_ID/$RUNNER_LABEL"

launchctl kickstart -k \
    "gui/$USER_ID/$WEB_LABEL"

echo
echo "GitSync installed."
echo
echo "Dashboard:"
echo "  http://127.0.0.1:8765"
echo
echo "Schedule:"
echo "  Monday-Friday at 10:30 AM"
echo
echo "Logs:"
echo "  $LOG_DIR"
