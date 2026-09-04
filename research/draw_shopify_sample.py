#!/usr/bin/env python3
"""Draw a random sample of RAW Shopify domains from the big combined_domains.csv
(domain + platform, ~8M rows) with reservoir sampling (constant memory, no need to
load 8M rows). Feeds the Shopify-Inbox density probe.

    python research/draw_shopify_sample.py <combined_domains.csv> -n 1000 > raw_shopify_sample.txt

Assumes the known schema: column 0 = domain, column 1 = platform. A header row (first
cell 'domain' / first platform cell 'platform') is auto-skipped. Deterministic via --seed
so a rerun probes the same stores.
"""
from __future__ import annotations

import argparse
import csv
import random
import sys


def sample_domains(rows, n: int, rng: random.Random, plat_col=1, dom_col=0,
                   want="shopify"):
    """Reservoir-sample n domains whose platform column == want. `rows` is an iterable of
    CSV row lists. Returns (reservoir, matched_total)."""
    reservoir: list[str] = []
    matched = 0
    for i, row in enumerate(rows):
        if len(row) <= max(plat_col, dom_col):
            continue
        plat = row[plat_col].strip().lower()
        if i == 0 and plat in ("platform", "cms", "technology"):   # header row
            continue
        if plat != want:
            continue
        dom = row[dom_col].strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
        if not dom:
            continue
        matched += 1
        if len(reservoir) < n:
            reservoir.append(dom)
        else:
            j = rng.randint(0, matched - 1)
            if j < n:
                reservoir[j] = dom
    return reservoir, matched


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("-n", type=int, default=1000, help="sample size")
    ap.add_argument("--platform", default="shopify")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)

    rng = random.Random(args.seed)
    with open(args.csv_path, newline="", encoding="utf-8", errors="replace") as f:
        reservoir, matched = sample_domains(csv.reader(f), args.n, rng, want=args.platform.lower())
    for d in reservoir:
        print(d)
    print(f"# sampled {len(reservoir)} of {matched} {args.platform} rows", file=sys.stderr)


if __name__ == "__main__":
    main()
