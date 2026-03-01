#!/usr/bin/env python3
"""
IMAP notification checker for Arena för lärande.
Checks for unread 'Ny information från Arena' emails, marks them read.
Outputs JSON: {"has_notifications": true, "count": 2, "message_ids": ["1234", "5678"]}

Reads credentials from environment variables:
  IMAP_SERVER, IMAP_PORT, IMAP_USERNAME, IMAP_PASSWORD
"""

import imaplib
import ssl
import json
import os
import sys

IMAP_SERVER = os.environ.get("IMAP_SERVER", "imap.mail.me.com")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
IMAP_USERNAME = os.environ["IMAP_USERNAME"]
IMAP_PASSWORD = os.environ["IMAP_PASSWORD"]


def main():
    try:
        ctx = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, ssl_context=ctx)
        mail.login(IMAP_USERNAME, IMAP_PASSWORD)
        mail.select("INBOX")

        status, data = mail.search(None, '(UNSEEN SUBJECT "Ny information")')
        if status != "OK" or not data[0]:
            mail.logout()
            print(json.dumps({"has_notifications": False, "count": 0, "message_ids": []}))
            return

        ids = data[0].split()
        message_ids = [mid.decode() for mid in ids]
        count = len(message_ids)

        for msg_id in ids:
            mail.store(msg_id, "+FLAGS", "\\Seen")

        mail.logout()
        print(json.dumps({"has_notifications": True, "count": count, "message_ids": message_ids}))

    except Exception as e:
        # On IMAP failure, signal to proceed anyway so we don't miss news
        print(json.dumps({"has_notifications": True, "count": 0, "error": str(e)}), file=sys.stderr)
        print(json.dumps({"has_notifications": True, "count": 0, "message_ids": []}))


if __name__ == "__main__":
    main()
