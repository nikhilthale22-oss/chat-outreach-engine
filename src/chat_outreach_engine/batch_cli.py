"""CLI for the batch runner - the volume engine.

    uv run python -m chat_outreach_engine.batch_cli domains.txt [--send] [opts]

Reads one domain per line (blank lines and # comments ignored). Dry-run by default: it
assesses every Brand and shows exactly what it WOULD pitch (vendor, A/B variant) without
sending. Pass --send to actually pitch. Resumable: Brands the Ledger already moved past
Queued are skipped, so re-running continues where it left off.

Residential proxy (Server #1): set PROXY_SERVER / PROXY_USERNAME / PROXY_PASSWORD in the env.
Visible browser per send: HEADED=1.
"""
from __future__ import annotations

import argparse
import sys

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
from .batch import BatchRunner, ForcedVendorAssessor
from .ledger import Ledger


def _read_domains(path: str) -> list[str]:
    if path == "-":
        lines = sys.stdin.read().splitlines()
    else:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    out = []
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        # tolerate CSV: take the first field, strip a scheme/path if present
        ln = ln.split(",")[0].strip().lower()
        ln = ln.replace("https://", "").replace("http://", "").split("/")[0]
        if ln:
            out.append(ln)
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("domains_file", help="file with one domain per line, or - for stdin")
    ap.add_argument("--send", action="store_true", help="actually pitch (default: dry-run)")
    ap.add_argument("--email", default="nikhilthale18@gmail.com")
    ap.add_argument("--db", default="ledger.db")
    ap.add_argument("--concurrency", type=int, default=8, help="browser send concurrency")
    ap.add_argument("--assess-concurrency", type=int, default=16,
                    help="HTTP assessment concurrency (higher; light work)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--max-attempts", type=int, default=4,
                    help="mark a Brand Dead after this many failed sends (stops forever-retry)")
    ap.add_argument("--vendors", default="tidio",
                    help="comma-separated vendors to enable (default tidio; gorgias send is "
                         "not yet delivery-confirmed)")
    ap.add_argument("--force-vendor", default=None,
                    help="treat the whole list as this vendor, skipping static detection (use for "
                         "shopify-inbox, whose JS-injected widget the static detector misses)")
    args = ap.parse_args(argv)

    domains = _read_domains(args.domains_file)
    ledger = Ledger(args.db)
    available = {"gorgias": GorgiasAdapter(), "tidio": TidioAdapter(), "tawk.to": TawkAdapter(),
                 "livechat": LiveChatAdapter(), "chatra": ChatraAdapter(), "intercom": IntercomAdapter(),
                 "helpscout": HelpScoutAdapter(), "zendesk": ZendeskAdapter(),
                 "shopify-inbox": ShopifyInboxAdapter(), "crisp": CrispAdapter(),
                 "reamaze": ReamazeAdapter(), "olark": OlarkAdapter(),
                 "zoho-salesiq": ZohoSalesIQAdapter()}
    enabled = {v.strip() for v in args.vendors.split(",") if v.strip()}
    if args.force_vendor:
        enabled.add(args.force_vendor)
    adapters = {k: a for k, a in available.items() if k in enabled}
    assessor = ForcedVendorAssessor(args.force_vendor) if args.force_vendor else None
    runner = BatchRunner(ledger, adapters, args.email, assessor=assessor,
                         concurrency=args.concurrency, assess_concurrency=args.assess_concurrency,
                         max_attempts=args.max_attempts, on_event=lambda m: print(m, flush=True))

    report = runner.run(domains, dry_run=not args.send, limit=args.limit)

    print("\n=== batch report ===")
    print(report.summary())
    for o in report.outcomes:
        tag = o.variant or "-"
        print(f"  {o.domain}: {o.action} [{tag}] - {o.reason} (vendor={o.vendor})")


if __name__ == "__main__":
    main()
