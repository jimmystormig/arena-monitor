#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# Arena News Monitor - Setup Script for macOS
# ──────────────────────────────────────────────────────────────────────────────
# This script:
#   1. Creates a Python virtual environment
#   2. Installs dependencies (playwright, beautifulsoup4)
#   3. Installs Playwright's Chromium browser
#   4. Installs a macOS launchd job to run every 4 hours
# ──────────────────────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PLIST_NAME="com.stormig.arena-monitor"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
LOG_DIR="$SCRIPT_DIR/logs"

echo "╔══════════════════════════════════════════════════════╗"
echo "║       Arena News Monitor - Setup                     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Step 1: Check Python 3
echo "→ Checking Python 3..."
if command -v python3 &>/dev/null; then
    PYTHON=$(command -v python3)
    echo "  Found: $PYTHON ($($PYTHON --version))"
else
    echo "  ✗ Python 3 not found. Please install Python 3 first."
    echo "    brew install python3"
    exit 1
fi

# Step 2: Create virtual environment
echo ""
echo "→ Creating virtual environment..."
if [ -d "$VENV_DIR" ]; then
    echo "  Virtual environment already exists, updating..."
else
    $PYTHON -m venv "$VENV_DIR"
    echo "  Created at $VENV_DIR"
fi

# Step 3: Install dependencies
echo ""
echo "→ Installing Python dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install playwright beautifulsoup4 anthropic python-dotenv -q
echo "  ✓ Dependencies installed"

# Step 4: Install Playwright Chromium
echo ""
echo "→ Installing Playwright Chromium browser..."
"$VENV_DIR/bin/playwright" install chromium
echo "  ✓ Chromium installed"

# Step 5: Create logs directory
echo ""
echo "→ Creating logs directory..."
mkdir -p "$LOG_DIR"
echo "  ✓ Logs will be written to $LOG_DIR"

# Step 6: Create launchd plist for scheduling (every 4 hours)
echo ""
echo "→ Setting up macOS launchd schedule (every 4 hours)..."

mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST_PATH" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${SCRIPT_DIR}/run.sh</string>
    </array>

    <key>StartInterval</key>
    <integer>14400</integer>

    <key>RunAtLoad</key>
    <true/>

    <key>StandardOutPath</key>
    <string>${LOG_DIR}/arena-monitor.log</string>

    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/arena-monitor-error.log</string>

    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>${HOME}</string>
    </dict>
</dict>
</plist>
PLISTEOF

echo "  ✓ Created $PLIST_PATH"

# Step 7: Load the launchd job
echo ""
echo "→ Loading the scheduled job..."

# Unload first if already loaded
launchctl bootout gui/$(id -u) "$PLIST_PATH" 2>/dev/null || true
launchctl bootstrap gui/$(id -u) "$PLIST_PATH"

echo "  ✓ Job loaded and scheduled"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✓ Setup complete!                                   ║"
echo "║                                                      ║"
echo "║  The monitor will run every 4 hours automatically.   ║"
echo "║                                                      ║"
echo "║  Useful commands:                                    ║"
echo "║    Run manually:                                     ║"
echo "║      bash $SCRIPT_DIR/run.sh"
echo "║                                                      ║"
echo "║    View logs:                                        ║"
echo "║      tail -f $LOG_DIR/arena-monitor.log"
echo "║                                                      ║"
echo "║    Stop the schedule:                                ║"
echo "║      launchctl bootout gui/\$(id -u) $PLIST_PATH"
echo "║                                                      ║"
echo "║    Restart the schedule:                             ║"
echo "║      launchctl bootstrap gui/\$(id -u) $PLIST_PATH"
echo "╚══════════════════════════════════════════════════════╝"
