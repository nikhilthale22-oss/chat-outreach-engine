"""CLI for the Reply Watcher - poll the gate inbox once and mark replying Brands Replied.

    IMAP_USER=nikhilmercwise@zohomail.in IMAP_APP_PASSWORD=xxxx \
        uv run python -m chat_outreach_engine.reply_watcher_cli --db ledger.db

Uses a Zoho app-specific password over IMAP SSL (imap.zoho.in, the India DC that serves
@zohomail.in addresses). This is a dedicated outreach inbox, not a personal account, so a spam
flag or ban here costs nothing. Run it on a schedule (cron) to keep the Ledger's Replied stage
current. Prints each match and the unmatched messages (so we can see the real reply format and
refine the matcher).
"""
from __future__ import annotations

import argparse
import datetime as dt
import os

from .ledger import Ledger
from .reply_watcher import ReplyWatcher, imap_fetch_unseen


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="ledger.db")
    ap.add_argument("--host", default=os.environ.get("IMAP_HOST", "imap.zoho.in"))
    ap.add_argument("--mailbox", default="INBOX")
    ap.add_argument("--user", default=os.environ.get("IMAP_USER", "nikhilmercwise@zohomail.in"))
    ap.add_argument("--since-days", type=int, default=7,
                    help="only scan mail received in the last N days (0 = all). Default to a recent "
                         "window so a re-run does not rescan the whole backlog.")
    ap.add_argument("--quiet", action="store_true",
                    help="suppress per-message 'unmatched' logging. Use for cron so senders/subjects "
                         "are not written to log files; matches and the summary still print.")
    args = ap.parse_args(argv)

    password = os.environ.get("IMAP_APP_PASSWORD")
    if not password:
        raise SystemExit("set IMAP_APP_PASSWORD (a Zoho app-specific password) in the environment")

    since = None
    if args.since_days and args.since_days > 0:
        since = (dt.datetime.now() - dt.timedelta(days=args.since_days)).strftime("%d-%b-%Y")

    ledger = Ledger(args.db)
    fetch = imap_fetch_unseen(args.host, args.user, password, args.mailbox, since=since)

    def emit(m):
        if (not args.quiet) or m.startswith("REPLIED"):
            print(m, flush=True)

    watcher = ReplyWatcher(ledger, fetch, on_event=emit)
    results = watcher.poll()
    matched = [d for _, d in results if d]
    print(f"\npolled {len(results)} new messages | {len(matched)} matched to a Pitched Brand "
          f"-> Replied | {len(results) - len(matched)} unmatched")


if __name__ == "__main__":
    main()
