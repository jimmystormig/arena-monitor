#!/usr/bin/env python3
"""
Email sender for Arena news notifications.
Reads a JSON payload from stdin or a file and sends an email.

Input JSON (stdin):
{
  "to": "jimmy@stormig.com",
  "subject": "[Arena - FIRSTNAME LASTNAME] Nyhet: ...",
  "body_text": "Plain text body...",
  "body_html": "<html>...</html>"
}

Reads SMTP credentials from environment variables:
  SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM
"""

import json
import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.mail.me.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ["SMTP_USERNAME"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USERNAME)


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    to = payload.get("to")
    subject = payload.get("subject")
    body_text = payload.get("body_text", "")
    body_html = payload.get("body_html", "")

    if not to or not subject:
        print("ERROR: 'to' and 'subject' are required", file=sys.stderr)
        sys.exit(1)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to

    if body_text:
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
    if body_html:
        msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"OK: Email sent to {to}: {subject}")
    except Exception as e:
        print(f"ERROR: SMTP failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
