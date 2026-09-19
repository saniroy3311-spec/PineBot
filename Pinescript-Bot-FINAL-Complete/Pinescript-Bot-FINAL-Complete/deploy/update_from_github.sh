#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${APP_DIR:-/opt/pinescript-bot}"
BRANCH="${BRANCH:-main}"
cd "$APP_DIR"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"
"$APP_DIR/.venv/bin/pip" install -r requirements.txt
systemctl restart pinescript_bot
systemctl --no-pager --full status pinescript_bot
