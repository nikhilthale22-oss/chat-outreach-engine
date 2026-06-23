"""CLI for a single live (or dry-run) pitch - used for the HITL live-send test.

    uv run python -m chat_outreach_engine.cli <domain> [--send] [--email X] [--db ...]

Dry-run by default: it detects the vendor and qualifies the Brand but sends
nothing. Pass --send to actually pitch a real Brand (HITL step).
"""
from __future__ import annotations

import argparse

from .adapters import GorgiasAdapter
from .detect import SignatureDetector
from .injector import Injector
from .ledger import Ledger

DEFAULT_PITCH = (
    "Hey, saw you don't have an AI chatbot on your site. "
    "I can build one that converts your shoppers (increases your CVR). "
    "Built one recently for Tusq apparel. "
    "I'll build it for free on a mock site first so you can test it, "
    "and we only make it live once you are satisfied. Would you be interested?\n\n"
    "Nikhil Thale, Founder, Postlist\n"
    "(flat $100/month for the first 10 clients since I'm gathering feedback)"
)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("domain")
    ap.add_argument("--send", action="store_true", help="actually send (default is dry-run)")
    ap.add_argument("--email", default="nikhilthale18@gmail.com")
    ap.add_argument("--pitch", default=DEFAULT_PITCH)
    ap.add_argument("--variant", default="A")
    ap.add_argument("--db", default="ledger.db")
    args = ap.parse_args(argv)

    domain = args.domain.strip()
    ledger = Ledger(args.db)
    injector = Injector(ledger, SignatureDetector(), {"gorgias": GorgiasAdapter()})
    out = injector.process(
        domain, args.pitch, args.email, pitch_variant=args.variant, dry_run=not args.send
    )
    print(f"{out.domain}: {out.action} - {out.reason} (vendor={out.vendor})")
    print(f"ledger stage -> {ledger.get_stage(domain)}")


if __name__ == "__main__":
    main()
