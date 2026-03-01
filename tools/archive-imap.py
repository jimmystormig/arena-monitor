#!/usr/bin/env python3
"""
Archive IMAP emails by message ID.
Reads a JSON payload from stdin with field "message_ids" (list of IMAP ID strings).
Copies each message to the archive folder, flags as deleted, then expunges.

Reads credentials from environment variables:
  IMAP_SERVER, IMAP_PORT, IMAP_USERNAME, IMAP_PASSWORD
  IMAP_ARCHIVE_FOLDER (default: "Archive")
"""

import imaplib
import json
import os
import ssl
import sys

IMAP_SERVER = os.environ.get("IMAP_SERVER", "imap.mail.me.com")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
IMAP_USERNAME = os.environ["IMAP_USERNAME"]
IMAP_PASSWORD = os.environ["IMAP_PASSWORD"]
IMAP_ARCHIVE_FOLDER = os.environ.get("IMAP_ARCHIVE_FOLDER", "Archive")


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(json.dumps({"archived": 0, "error": f"Invalid JSON input: {e}"}))
        return

    message_ids = payload.get("message_ids", [])
    if not message_ids:
        print(json.dumps({"archived": 0}))
        return

    try:
        ctx = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, ssl_context=ctx)
        mail.login(IMAP_USERNAME, IMAP_PASSWORD)
        mail.select("INBOX")

        archived = 0
        for mid in message_ids:
            msg_id = mid.encode() if isinstance(mid, str) else mid
            status, _ = mail.copy(msg_id, IMAP_ARCHIVE_FOLDER)
            if status == "OK":
                mail.store(msg_id, "+FLAGS", "\\Deleted")
                archived += 1

        mail.expunge()
        mail.logout()
        print(json.dumps({"archived": archived}))

    except Exception as e:
        print(json.dumps({"archived": 0, "error": str(e)}))


if __name__ == "__main__":
    main()
