#!/bin/bash
# Arena Monitor — Agent SDK runner
# Scheduled via launchd every 4 hours.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Load credentials from .env
set -a
# shellcheck source=.env
source "$SCRIPT_DIR/.env"
set +a

mkdir -p "$SCRIPT_DIR/logs"

echo "--- Arena Monitor run: $(date '+%Y-%m-%d %H:%M:%S') ---"

"$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/agent.py"
