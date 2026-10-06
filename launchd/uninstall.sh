#!/bin/bash

set -e

USER_ID="$(id -u)"

WEB_LABEL="com.local.gitsync.web"
RUNNER_LABEL="com.local.gitsync.runner"

WEB_PLIST="$HOME/Library/LaunchAgents/$WEB_LABEL.plist"
RUNNER_PLIST="$HOME/Library/LaunchAgents/$RUNNER_LABEL.plist"

launchctl bootout \
    "gui/$USER_ID/$WEB_LABEL" \
    2>/dev/null || true

launchctl bootout \
    "gui/$USER_ID/$RUNNER_LABEL" \
    2>/dev/null || true

rm -f "$WEB_PLIST"
rm -f "$RUNNER_PLIST"

echo
echo "GitSync launch agents removed."
echo
echo "Application data was preserved:"
echo "  $HOME/.gitsync/"
echo
echo "To remove that as well:"
echo "  rm -rf $HOME/.gitsync"
echo
