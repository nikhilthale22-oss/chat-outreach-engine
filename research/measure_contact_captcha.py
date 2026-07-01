#!/usr/bin/env python3
"""Measure the Shopify contact-form hCaptcha pass rate, DIRECT vs PROXY, WITHOUT sending anything:
fill the form, click submit, but ABORT any POST to /contact (so no merchant receives a message). If a
POST is attempted -> hCaptcha passed (would_pass). If an hCaptcha challenge appears instead -> challenged.
Images/media/fonts blocked to save proxy bandwidth.

Usage: python3 research/measure_contact_captcha.py <list.txt> [N]
"""
import os, random, sys, time
sys.path.insert(0, "/root/chat-outreach-engine/src")
from chat_outreach_engine.adapters.shopify_contact_form import ShopifyContactFormAdapter
from chat_outreach_engine.pitches import PITCH_A

a = ShopifyContactFormAdapter()
BLOCK = {"image", "media", "font"}
CAPTCHA_JS = """() => !!document.querySelector("iframe[src*='hcaptcha'], iframe[title*='captcha' i], .h-captcha, [id*='hcaptcha'], iframe[src*='recaptcha']")"""


def proxy_dict():
    e = {}
    with open("/root/chat-outreach-engine/.env.proxy") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1); e[k] = v
    return {"server": e["PROXY_SERVER"], "username": e["PROXY_USERNAME"], "password": e["PROXY_PASSWORD"]}


def one(p, domain, mode):
    b = p.chromium.launch(headless=True, channel=None, args=["--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(viewport={"width":1366,"height":900}, locale="en-US",
                        proxy=proxy_dict() if mode == "proxy" else None)
    state = {"post_attempted": False}

    def route(r):
        req = r.request
        if req.method == "POST" and "/contact" in req.url:
            state["post_attempted"] = True
            try: r.abort()
            except Exception: pass
            return
        if req.resource_type in BLOCK:
            try: r.abort()
            except Exception: pass
            return
        try: r.continue_()
        except Exception: pass

    ctx.route("**/*", route)
    page = ctx.new_page()
    verdict = "no_form"
    try:
        form = a._find_form(page, domain)
        if form is not None:
            a._fill(form, PITCH_A, "noreply@example.com")
            try:
                form.locator("button[type=submit], input[type=submit]").first.click(timeout=5000, force=True)
            except Exception:
                pass
            time.sleep(5)
            captcha = False
            try: captcha = page.evaluate(CAPTCHA_JS)
            except Exception: pass
            if state["post_attempted"]:
                verdict = "would_pass"
            elif captcha:
                verdict = "challenged"
            else:
                verdict = "unknown"
    except Exception as e:
        verdict = f"err:{type(e).__name__}"
    b.close()
    return verdict


def main():
    lst, n = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 10
    domains = [x.strip() for x in open(lst) if x.strip()]
    random.seed(77); random.shuffle(domains); domains = domains[:n]
    from playwright.sync_api import sync_playwright
    tally = {"direct": {}, "proxy": {}}
    with sync_playwright() as p:
        for d in domains:
            vd = one(p, d, "direct"); vp = one(p, d, "proxy")
            tally["direct"][vd] = tally["direct"].get(vd, 0) + 1
            tally["proxy"][vp] = tally["proxy"].get(vp, 0) + 1
            print(f"{d:38} direct={vd:12} proxy={vp:12}")
            sys.stdout.flush()
    for mode in ("direct", "proxy"):
        t = tally[mode]; tot = sum(t.values())
        wp = t.get("would_pass", 0)
        print(f"\n== {mode}: would_pass {wp}/{tot} ({100*wp//max(1,tot)}%)  breakdown={t}")


if __name__ == "__main__":
    main()
