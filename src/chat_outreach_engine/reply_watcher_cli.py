"""CLI for the Reply Watcher - poll the gate inbox once and mark replying Brands Replied.

    IMAP_USER=nikhilthale18@gmail.com IMAP_APP_PASSWORD=xxxx \
        uv run python -m chat_outreach_engine.reply_watcher_cli --db ledger.db

Uses a Gmail app password over IMAP SSL (imap.gmail.com). Run it on a schedule (cron) to keep
the Ledger's Replied stage current. Prints each match and the unmatched messages (so we can see
the real reply format and refine the matcher).
"""
from __future__ import annotations

import argparse
import os

from .ledger import Ledger
from .reply_watcher import ReplyWatcher, imap_fetch_unseen


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="ledger.db")
    ap.add_argument("--host", default="imap.gmail.com")
    ap.add_argument("--mailbox", default="INBOX")
    ap.add_argument("--user", default=os.environ.get("IMAP_USER", "nikhilthale18@gmail.com"))
    args = ap.parse_args(argv)

    password = os.environ.get("IMAP_APP_PASSWORD")
    if not password:
        raise SystemExit("set IMAP_APP_PASSWORD (a Gmail app password) in the environment")

    ledger = Ledger(args.db)
    fetch = imap_fetch_unseen(args.host, args.user, password, args.mailbox)
    watcher = ReplyWatcher(ledger, fetch, on_event=lambda m: print(m, flush=True))
    results = watcher.poll()
    matched = [d for _, d in results if d]
    print(f"\npolled {len(results)} new messages | {len(matched)} matched to a Pitched Brand "
          f"-> Replied | {len(results) - len(matched)} unmatched")


if __name__ == "__main__":
    main()
