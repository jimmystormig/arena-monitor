"""
Arena Monitor — Anthropic Agent SDK agent.

Replaces the claude CLI + arena-monitor-prompt.md approach with a proper
Python agent that calls typed tools. The three Python tool scripts are
unchanged; this file orchestrates them via structured tool_use calls.
"""

import json
import os
import subprocess
import sys
from datetime import datetime

import anthropic
from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(SCRIPT_DIR, ".venv", "bin", "python")
SEEN_NEWS_FILE = os.path.join(SCRIPT_DIR, ".arena-seen-news.json")

client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "check_imap",
        "description": "Check iCloud Mail for unread Arena notifications. Returns JSON with has_notifications (bool) and count (int). If has_notifications is false, stop — do not scrape.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "scrape_arena",
        "description": "Log into Arena för lärande and scrape news items for all children. Returns a JSON array of news items, each with: child, title, date, url, content_text, content_html.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max news items to fetch per child. Default 5.",
                }
            },
        },
    },
    {
        "name": "read_seen_news",
        "description": "Read the list of already-processed news URLs from .arena-seen-news.json. Returns a JSON array of URL strings. Returns [] if file does not exist.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "write_seen_news",
        "description": "Persist the updated list of seen news URLs to .arena-seen-news.json. Pass ALL URLs (previously seen + newly processed), they will be sorted and deduplicated.",
        "input_schema": {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "All seen URLs to persist.",
                }
            },
            "required": ["urls"],
        },
    },
    {
        "name": "send_email",
        "description": "Send an email via SMTP (iCloud Mail). Use SMTP_TO env var for the recipient.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address."},
                "subject": {"type": "string", "description": "Email subject line."},
                "body_text": {"type": "string", "description": "Plain text email body."},
                "body_html": {"type": "string", "description": "HTML email body."},
            },
            "required": ["to", "subject", "body_text", "body_html"],
        },
    },
]

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


def run_tool(name: str, inputs: dict) -> str:
    if name == "check_imap":
        result = subprocess.run(
            [VENV_PYTHON, os.path.join(SCRIPT_DIR, "tools", "check-imap.py")],
            capture_output=True,
            text=True,
            cwd=SCRIPT_DIR,
        )
        return result.stdout or result.stderr

    elif name == "scrape_arena":
        limit = inputs.get("limit", 5)
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

    elif name == "read_seen_news":
        try:
            with open(SEEN_NEWS_FILE) as f:
                return f.read()
        except FileNotFoundError:
            return "[]"

    elif name == "write_seen_news":
        urls = sorted(set(inputs["urls"]))
        with open(SEEN_NEWS_FILE, "w") as f:
            json.dump(urls, f, indent=2, ensure_ascii=False)
        return json.dumps({"ok": True, "count": len(urls)})

    elif name == "send_email":
        result = subprocess.run(
            [VENV_PYTHON, os.path.join(SCRIPT_DIR, "tools", "send-email.py")],
            input=json.dumps(inputs),
            capture_output=True,
            text=True,
            cwd=SCRIPT_DIR,
        )
        return result.stdout or result.stderr

    return json.dumps({"error": f"Unknown tool: {name}"})


LOG_FILE = os.path.join(SCRIPT_DIR, "logs", "runs.log")


def append_log(summary: str):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp}  {summary}\n")


def main():
    messages = [{"role": "user", "content": "Kör arena-monitor nu."}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8096,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            summary = ""
            for block in response.content:
                if hasattr(block, "text"):
                    summary = block.text
                    print(summary)
            append_log(summary)
            break

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"[tool] {block.name}({json.dumps(block.input)})", file=sys.stderr)
                result = run_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )

        if tool_results:
            messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    main()
