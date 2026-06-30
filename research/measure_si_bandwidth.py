#!/usr/bin/env python3
"""Run ON Server #1. Measures REAL per-store bandwidth for Shopify Inbox stores loaded through the
ProxyBase residential proxy, in two modes: full, and images/media/fonts blocked. Uses Chromium's CDP
Network events (encodedDataLength = actual wire bytes). Also records whether the SI widget element
appears (reach through residential). No sends, no ledger. Projects the full-pool cost.

Usage: python3 measure_si_bandwidth.py <si_list.txt> [N]
"""
import os, random, sys, time

with open("/root/chat-outreach-engine/.env.proxy") as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1); os.environ[k] = v

sys.path.insert(0, "/root/chat-outreach-engine/src")
from chat_outreach_engine.proxy import playwright_proxy

BLOCK = {"image", "media", "font"}
SI_PRESENT_JS = "() => !!document.querySelector('inbox-online-store-chat')"


def measure(p, domain, block_media):
    browser = p.chromium.launch(headless=True, channel=None,
                                args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(proxy=playwright_proxy(), viewport={"width": 1366, "height": 900},
                              locale="en-US")
    page = ctx.new_page()
    total = {"bytes": 0}
    cdp = ctx.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.on("Network.loadingFinished", lambda e: total.__setitem__("bytes", total["bytes"] + e.get("encodedDataLength", 0)))
    if block_media:
        page.route("**/*", lambda route: route.abort()
                   if route.request.resource_type in BLOCK else route.continue_())
    ok, si = False, False
    try:
        page.goto("https://" + domain, wait_until="domcontentloaded", timeout=40000)
        ok = True
        time.sleep(6)  # let the SI bundle inject
        try:
            si = page.evaluate(SI_PRESENT_JS)
        except Exception:
            si = False
    except Exception:
        ok = False
    finally:
        mb = total["bytes"] / 1_000_000
        browser.close()
    return ok, si, mb


def main():
    lst, n = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 8
    domains = [x.strip() for x in open(lst) if x.strip()]
    random.seed(13); random.shuffle(domains); domains = domains[:n]
    from playwright.sync_api import sync_playwright
    rows = []
    with sync_playwright() as p:
        for d in domains:
            ok_f, si_f, mb_f = measure(p, d, block_media=False)
            ok_b, si_b, mb_b = measure(p, d, block_media=True)
            rows.append((d, ok_f, si_f, mb_f, mb_b))
            print(f"{d:40} full: load={ok_f} si={si_f} {mb_f:5.2f}MB | noimg: {mb_b:5.2f}MB")
            sys.stdout.flush()
    loaded = [r for r in rows if r[1]]
    si_seen = [r for r in rows if r[2]]
    if loaded:
        avg_full = sum(r[3] for r in loaded) / len(loaded)
        avg_noimg = sum(r[4] for r in loaded) / len(loaded)
        print(f"\n== {len(loaded)}/{len(rows)} loaded through proxy; SI widget seen on {len(si_seen)} ==")
        print(f"avg per store: full {avg_full:.2f} MB | images-blocked {avg_noimg:.2f} MB "
              f"({100*(1-avg_noimg/avg_full):.0f}% saved)")
        print(f"projected FULL SI pool (73,514): full {avg_full*73514/1000:.1f} GB | "
              f"images-blocked {avg_noimg*73514/1000:.1f} GB  (balance = 33 GiB)")
        print(f"this test consumed ~{sum(r[3]+r[4] for r in rows):.1f} MB total")


if __name__ == "__main__":
    main()
