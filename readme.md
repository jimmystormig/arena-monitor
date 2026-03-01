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
```

`agent.py` runs a Claude model via the Agent SDK. The model orchestrates the
flow and writes intelligent Swedish summaries. Tools are exposed via an MCP
server. Credentials are loaded from `.env`.

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

   tools/mcp_server.py    — stdio MCP server, wraps the three tools below
   tools/check-imap.py    — Check for unread Arena notification emails → JSON
   tools/arena-scraper.py — Log into Arena, scrape news with full content → JSON
   tools/send-email.py    — Send an email (reads JSON payload from stdin)
