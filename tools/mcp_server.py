"""
Arena Monitor — MCP stdio server.

Exposes the five arena-monitor tools via the MCP protocol so the
claude-agent-sdk can spawn this as an external MCP server process.
"""

import json
import os
import subprocess
import sys

from mcp.server.fastmcp import FastMCP

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(SCRIPT_DIR, ".venv", "bin", "python")
SEEN_NEWS_FILE = os.path.join(SCRIPT_DIR, ".arena-seen-news.json")

mcp = FastMCP("arena-tools")


@mcp.tool()
def check_imap() -> str:
    """Check iCloud Mail for unread Arena notifications. Returns JSON with has_notifications (bool) and count (int). If has_notifications is false, stop — do not scrape."""
    result = subprocess.run(
        [VENV_PYTHON, os.path.join(SCRIPT_DIR, "tools", "check-imap.py")],
        capture_output=True,
        text=True,
        cwd=SCRIPT_DIR,
    )
    return result.stdout or result.stderr


@mcp.tool()
def scrape_arena(limit: int = 5) -> str:
    """Log into Arena för lärande and scrape news items for all children. Returns a JSON array of news items, each with: child, title, date, url, content_text, content_html."""
    result = subprocess.run(
        [
            VENV_PYTHON,
            os.path.join(SCRIPT_DIR, "tools", "arena-scraper.py"),
            "--limit",
            str(limit),
        ],
        capture_output=True,
        text=True,
        cwd=SCRIPT_DIR,
    )
    return result.stdout or result.stderr


@mcp.tool()
def read_seen_news() -> str:
    """Read the list of already-processed news URLs from .arena-seen-news.json. Returns a JSON array of URL strings. Returns [] if file does not exist."""
    try:
        with open(SEEN_NEWS_FILE) as f:
            return f.read()
    except FileNotFoundError:
        return "[]"


@mcp.tool()
def write_seen_news(urls: list[str]) -> str:
    """Persist the updated list of seen news URLs to .arena-seen-news.json. Pass ALL URLs (previously seen + newly processed), they will be sorted and deduplicated."""
    deduped = sorted(set(urls))
    with open(SEEN_NEWS_FILE, "w") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)
    return json.dumps({"ok": True, "count": len(deduped)})


@mcp.tool()
def send_email(to: str, subject: str, body_text: str, body_html: str) -> str:
    """Send an email via SMTP (iCloud Mail). Use SMTP_TO env var for the recipient."""
    payload = {
        "to": to,
        "subject": subject,
        "body_text": body_text,
        "body_html": body_html,
    }
    result = subprocess.run(
        [VENV_PYTHON, os.path.join(SCRIPT_DIR, "tools", "send-email.py")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=SCRIPT_DIR,
    )
    return result.stdout or result.stderr


if __name__ == "__main__":
    mcp.run(transport="stdio")
