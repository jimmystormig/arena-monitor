# Arena Monitor

Monitors Arena för lärande for new school news for registered children.
Runs as a scheduled Claude CLI agent every 4 hours.

## Architecture

```text
run.sh  ──►  agent.py (Claude Agent SDK)
                  ──►  tools/mcp_server.py (stdio MCP server)
                            ──►  tools/check-imap.py   (IMAP check)
                            ──►  tools/arena-scraper.py (Playwright scraper)
                            ──►  tools/send-email.py    (SMTP sender)
                            ──►  tools/archive-imap.py  (IMAP archiver)
```

`agent.py` runs a Claude model via the Agent SDK. The model orchestrates the
flow and writes intelligent Swedish summaries. Tools are exposed via an MCP
server. Credentials are loaded from `.env`.

## Installation

**Prerequisites:** Python 3.10+, macOS (launchd scheduling)

1. Clone the repo and enter the directory.

2. Copy `.env.example` to `.env` and fill in your credentials:

   ```text
   ARENA_URL        — URL to your school's Arena instance
   ARENA_USERNAME   — Arena login username
   ARENA_PASSWORD   — Arena login password

   IMAP_SERVER/PORT/USERNAME/PASSWORD  — IMAP account that receives Arena notifications
   IMAP_ARCHIVE_FOLDER                — IMAP folder for archived emails (default: "Archive")
   SMTP_SERVER/PORT/USERNAME/PASSWORD  — SMTP account used to send summary emails
   SMTP_FROM        — Sender address
   SMTP_TO          — Recipient address for summaries
   ```

3. Run the setup script (creates `.venv`, installs dependencies, installs Chromium, and registers the launchd job):

   ```bash
   ./setup.sh
   ```

   The monitor will immediately run once and then repeat every 4 hours automatically.

## Useful commands

   Run manually:
     ./run.sh

   Watch logs live:
     tail -f logs/runs.log

   Force a full run (clear seen-news to re-process everything):
     echo '[]' > .arena-seen-news.json && ./run.sh

   Stop the schedule:
     launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.stormig.arena-monitor.plist

   Restart the schedule:
     launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.stormig.arena-monitor.plist

## Tool scripts (exposed via MCP server)

   tools/mcp_server.py    — stdio MCP server, wraps the tools below
   tools/check-imap.py    — Check for unread Arena notification emails → JSON
   tools/arena-scraper.py — Log into Arena, scrape news with full content → JSON
   tools/send-email.py    — Send an email (reads JSON payload from stdin)
   tools/archive-imap.py  — Archive emails by IMAP message ID (reads JSON from stdin)
