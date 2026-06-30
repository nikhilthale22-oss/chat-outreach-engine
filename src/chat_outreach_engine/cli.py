"""CLI for a single live (or dry-run) pitch - used for the HITL live-send test.

    uv run python -m chat_outreach_engine.cli <domain> [--send] [--email X] [--db ...]

Dry-run by default: it detects the vendor and qualifies the Brand but sends
nothing. Pass --send to actually pitch a real Brand (HITL step).
"""
from __future__ import annotations

import argparse

from .adapters import (
    ChatraAdapter,
    CrispAdapter,
    GorgiasAdapter,
    HelpScoutAdapter,
    IntercomAdapter,
    LiveChatAdapter,
    OlarkAdapter,
    ReamazeAdapter,
    ShopifyInboxAdapter,
    TawkAdapter,
    TidioAdapter,
    ZendeskAdapter,
    ZohoSalesIQAdapter,
)
from .detect import SignatureDetector
from .injector import Injector
from .ledger import Ledger
from .pitches import PITCH_A

DEFAULT_PITCH = PITCH_A


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
    injector = Injector(ledger, SignatureDetector(),
                        {"gorgias": GorgiasAdapter(), "shopify-inbox": ShopifyInboxAdapter(),
                         "tidio": TidioAdapter(), "tawk.to": TawkAdapter(),
                         "livechat": LiveChatAdapter(), "chatra": ChatraAdapter(),
                         "intercom": IntercomAdapter(), "helpscout": HelpScoutAdapter(),
                         "zendesk": ZendeskAdapter(), "crisp": CrispAdapter(),
                         "reamaze": ReamazeAdapter(), "olark": OlarkAdapter(),
                         "zoho-salesiq": ZohoSalesIQAdapter()})
    out = injector.process(
        domain, args.pitch, args.email, pitch_variant=args.variant, dry_run=not args.send
    )
    print(f"{out.domain}: {out.action} - {out.reason} (vendor={out.vendor})")
    print(f"ledger stage -> {ledger.get_stage(domain)}")


if __name__ == "__main__":
    main()
