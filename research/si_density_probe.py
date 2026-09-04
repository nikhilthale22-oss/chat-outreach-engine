#!/usr/bin/env python3
"""SI DENSITY PROBE - measure the one unmeasured number that sizes the whole raw-pool play:
what fraction of RAW Shopify stores actually run a DRIVABLE Shopify Inbox widget.

Runs the REAL ShopifyInboxAdapter in dry_run mode against each store: it loads the page, checks
for the <inbox-online-store-chat> widget, and tries to reach the composer. It SENDS NOTHING -
dry_run stops at 'composer_reached' before any message is typed. So this is a safe, no-spam,
production-path measurement (the exact path a real send would take, minus the send).

    uv run python research/si_density_probe.py raw_shopify_sample.txt --concurrency 4

Read the bottom line: DRIVABLE Shopify Inbox = X% => raw-pool deliverable ~ 3.54M * X% * (send rate).
Buckets: composer_reached = drivable SI; no_shopify_inbox = no SI widget present; no_launcher /
no_composer = SI present but not drivable; error:* = load/other failure.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

from chat_outreach_engine.adapters.shopify_inbox import ShopifyInboxAdapter
from chat_outreach_engine.pitches import PITCH_A


def _domains(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            ln = ln.split(",")[0].strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
            if ln:
                yield ln


def probe_one(domain: str):
    """Real adapter, dry_run=True: loads + checks the widget, never sends. Returns (domain, detail)."""
    try:
        r = ShopifyInboxAdapter().send(domain, PITCH_A, "probe@example.com", dry_run=True)
        return domain, r.detail
    except Exception as e:
        return domain, f"error:{type(e).__name__}"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("domains_file")
    ap.add_argument("--concurrency", type=int, default=4, help="keep low - paced, gentle on IPs")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args(argv)

    doms = list(_domains(args.domains_file))
    if args.limit:
        doms = doms[: args.limit]

    tally: Counter = Counter()
    n = 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        for fut in as_completed([ex.submit(probe_one, d) for d in doms]):
            dom, detail = fut.result()
            tally[detail] += 1
            n += 1
            print(f"{dom}: {detail}", flush=True)

    drivable = tally.get("composer_reached", 0)
    present = drivable + tally.get("no_launcher", 0) + tally.get("no_composer", 0)
    print("\n=== SI density ===")
    print(f"probed: {n}")
    for k, v in tally.most_common():
        print(f"  {k}: {v} ({100 * v / max(1, n):.0f}%)")
    print(f"\nSI widget present (any): {present}/{n} = {100 * present / max(1, n):.1f}%")
    print(f"DRIVABLE Shopify Inbox:  {drivable}/{n} = {100 * drivable / max(1, n):.1f}%")
    if n:
        est_low = int(3_540_000 * (drivable / n) * 0.32)
        est_high = int(3_540_000 * (drivable / n) * 0.52)
        print(f"\n=> raw-pool one-time deliverable at this density ~ {est_low:,} - {est_high:,} "
              f"(3.54M x {100*drivable/n:.1f}% drivable x 32-52% measured send rate)")


if __name__ == "__main__":
    main()
