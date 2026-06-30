#!/usr/bin/env python3
"""Verify-to-composer for a vendor on a RANDOM sample, via the production path. Calls
WidgetDriver.send(dry_run=True) - it reaches the composer and returns "composer_reached" WITHOUT
typing or sending anything. Measures the real reach rate. Safe to run unattended (nothing transmits).

Usage: python3 research/verify_vendor.py <vendor> <list.txt> [N] [seed]
"""
import collections, random, sys

from chat_outreach_engine.adapters.olark import OLARK
from chat_outreach_engine.adapters.zoho_salesiq import ZOHO_SALESIQ
from chat_outreach_engine.widget_driver import WidgetDriver

CONFIGS = {"olark": OLARK, "zoho-salesiq": ZOHO_SALESIQ}


def main():
    vendor, lst = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 42
    domains = [x.strip() for x in open(lst) if x.strip()]
    random.seed(seed)
    random.shuffle(domains)
    domains = domains[:n]
    drv = WidgetDriver(CONFIGS[vendor])
    reached = 0
    tally = collections.Counter()
    for d in domains:
        r = drv.send(d, "verify probe", "noreply@example.com", dry_run=True)
        tag = r.detail if r.sent else f"FAIL:{r.detail}"
        tally[tag] += 1
        if r.sent and r.detail == "composer_reached":
            reached += 1
        print(f"{d:42} {'OK ' if r.sent else 'X  '}{r.detail}")
        sys.stdout.flush()
    print(f"\n== {vendor}: REACHED {reached}/{len(domains)} ({100*reached//max(1,len(domains))}%) ==")
    for k, v in tally.most_common():
        print(f"   {v:3}  {k}")


if __name__ == "__main__":
    main()
