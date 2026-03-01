"""
Arena Monitor — Claude Agent SDK agent.

Uses the claude-agent-sdk to route model calls through a Claude Code
subscription. The five tools are exposed via an external stdio MCP server
(tools/mcp_server.py); the agentic loop is handled by the SDK.
"""

import asyncio
import os
import sys
from datetime import datetime

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)
from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(SCRIPT_DIR, ".venv", "bin", "python")
MCP_SERVER = os.path.join(SCRIPT_DIR, "tools", "mcp_server.py")

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, Arial, sans-serif; max-width: 800px; margin: 0 auto; background: #f5f5f5; padding: 20px;">
  <div style="background: #1a5276; color: white; padding: 18px 24px; border-radius: 8px 8px 0 0;">
    <h2 style="margin: 0; font-size: 20px;">Arena för lärande</h2>
    <p style="margin: 6px 0 0; opacity: 0.9;">Nyhet för <strong>CHILD_NAME</strong> — DATE</p>
  </div>
  <div style="background: #fef9e7; border: 1px solid #f9e79f; padding: 16px 24px;">
    <h3 style="margin: 0 0 8px; color: #7d6608; font-size: 15px;">Sammanfattning</h3>
    <p style="margin: 0; color: #7d6608; font-size: 14px; line-height: 1.6;">SUMMARY_TEXT</p>
  </div>
  <div style="background: #eaf2f8; padding: 12px 24px; border-left: 1px solid #d4e6f1; border-right: 1px solid #d4e6f1;">
    <p style="margin: 4px 0; font-size: 13px;"><strong>Titel:</strong> TITLE</p>
    <p style="margin: 4px 0; font-size: 13px;"><strong>Länk:</strong> <a href="URL" style="color: #2980b9;">URL</a></p>
  </div>
  <div style="background: white; border: 1px solid #d5d8dc; padding: 24px; border-radius: 0 0 8px 8px;">
    <h3 style="margin: 0 0 12px; color: #2c3e50;">Fullständigt innehåll</h3>
    <hr style="border: none; border-top: 1px solid #eee; margin: 0 0 16px;">
    CONTENT_HTML
  </div>
  <p style="text-align: center; color: #aaa; font-size: 11px; margin-top: 16px;">
    Automatiskt skickat av Arena News Monitor
  </p>
</body></html>"""

SYSTEM = f"""Du är Arena Monitor, ett automatiserat system som bevakar skolnyheter för barnen. \
Du skickar korta, vänliga e-postsammanfattningar på svenska till föräldrarna \
när det finns nya nyheter på Arena för lärande.

Följ alltid dessa steg i exakt denna ordning:

1. Anropa check_imap. Om has_notifications är false, skriv \
"Inga nya notifieringar. Avslutar." och avsluta direkt.

2. Anropa scrape_arena (limit 5) för att hämta nyheter.

3. Anropa read_seen_news för att hämta listan med redan sedda URL:er. \
En nyhet är NY om dess url INTE finns i denna lista.

4. För varje ny nyhet, anropa send_email med:
   - to: värdet av miljövariabeln SMTP_TO
   - subject: "[Arena - CHILD_NAME] TITLE" där CHILD_NAME är barnets namn i title case
   - body_text: ren text-sammanfattning på svenska (2-4 meningar)
   - body_html: HTML-e-post baserad på mallen nedan

   Sammanfattningen ska fokusera på vad föräldrar behöver veta:
   - Kommande prov, läxförhör eller glosor
   - Läxor och inlämningar med deadlines
   - Utflykter, besök eller events
   - Studiedagar eller lov
   - Schemainformation eller betyg
   Skriv INTE bara om artikeltexten — syntetisera den till en föräldrarvänlig sammanfattning.

   HTML-mall (ersätt CHILD_NAME, DATE, SUMMARY_TEXT, TITLE, URL, CONTENT_HTML):
{HTML_TEMPLATE}

5. Anropa write_seen_news med ALLA URL:er (tidigare sedda + nya) för att uppdatera listan.

6. Skriv ut en kort sammanfattning på svenska, t.ex.:
   "Klart. Hittade 3 nya nyheter (2 för barn 1, 1 för barn 2). Skickade 3 e-postmeddelanden."
"""

# ---------------------------------------------------------------------------
# Query options — external stdio MCP server
# ---------------------------------------------------------------------------

OPTIONS = ClaudeAgentOptions(
    system_prompt=SYSTEM,
    mcp_servers={
        "arena-tools": {
            "command": VENV_PYTHON,
            "args": [MCP_SERVER],
        }
    },
    allowed_tools=[
        "mcp__arena-tools__check_imap",
        "mcp__arena-tools__scrape_arena",
        "mcp__arena-tools__read_seen_news",
        "mcp__arena-tools__write_seen_news",
        "mcp__arena-tools__send_email",
    ],
    model="claude-sonnet-4-6",
)

# ---------------------------------------------------------------------------
# Logging & main
# ---------------------------------------------------------------------------

LOG_FILE = os.path.join(SCRIPT_DIR, "logs", "runs.log")


def append_log(summary: str):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp}  {summary}\n")


async def main():
    summary = ""
    async for message in query(prompt="Kör arena-monitor nu.", options=OPTIONS):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text, file=sys.stderr)
        elif isinstance(message, ResultMessage) and message.result:
            summary = message.result
    print(summary)
    append_log(summary)


if __name__ == "__main__":
    asyncio.run(main())
