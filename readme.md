# Arena Monitor

Monitors Arena för lärande for new school news for registered children.
Runs as a scheduled Claude CLI agent every 4 hours.

## Architecture

```text
run.sh  ──►  claude CLI  ──►  tools/check-imap.py   (IMAP check)
                         ──►  tools/arena-scraper.py (Playwright scraper)
                         ──►  tools/send-email.py    (SMTP sender)
```

Claude orchestrates the flow and writes intelligent Swedish summaries.
Credentials are loaded from `.env`.

## Useful commands

   Run manually:
     ./run.sh

   Watch logs live:
     tail -f logs/arena-monitor.log

   Force a full run (clear seen-news to re-process everything):
     echo '[]' > .arena-seen-news.json && ./run.sh

   Stop the schedule:
     launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.stormig.arena-monitor.plist

   Restart the schedule:
     launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.stormig.arena-monitor.plist

## Tool scripts (called by Claude via Bash)

   tools/check-imap.py    — Check for unread Arena notification emails → JSON
   tools/arena-scraper.py — Log into Arena, scrape news with full content → JSON
   tools/send-email.py    — Send an email (reads JSON payload from stdin)
