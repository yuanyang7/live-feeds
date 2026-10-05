#!/bin/sh
# Install (or reinstall) a launchd agent that runs one feed from this machine
# whenever the published data has gone stale (see scripts/local_timer.py).
#
#   scripts/install-local-timer.sh <feed> [minute]
#
# It fires at <minute> past every hour (default 47, offset from the Actions cron
# at :17) and once at login, and catches up after the laptop wakes. Remove it:
#
#   launchctl bootout gui/$(id -u)/com.live-feeds.<feed>
set -eu

FEED="${1:?usage: install-local-timer.sh <feed> [minute]}"
MINUTE="${2:-47}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.live-feeds.$FEED"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$HOME/Library/Logs/live-feeds-$FEED.log"
PYTHON="$ROOT/.venv/bin/python"

[ -d "$ROOT/feeds/$FEED" ] || { echo "no feed at feeds/$FEED"; exit 1; }
[ -x "$PYTHON" ] || { echo "no venv at $PYTHON (see README, Local use)"; exit 1; }
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$ROOT/scripts/local_timer.py</string>
    <string>$FEED</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>StartCalendarInterval</key><dict><key>Minute</key><integer>$MINUTE</integer></dict>
  <key>RunAtLoad</key><true/>
  <key>ProcessType</key><string>Background</string>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/usr/bin:/bin:/usr/sbin:/sbin</string></dict>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "installed $LABEL at :$MINUTE past the hour; log: $LOG"
