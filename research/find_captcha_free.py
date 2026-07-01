#!/usr/bin/env python3
"""Find captcha-FREE Shopify contact forms + measure the free-subset rate. Headless, nothing sent:
fill + click submit, poll up to 12s for a POST to /contact (= no captcha; captcha-gated forms show a
challenge and never POST). Abort the POST so nothing is delivered. Writes the captcha-free domains to
a file so one can be used for the single real proof send.

Usage: python3 research/find_captcha_free.py <list.txt> [N] [seed] [out.txt]
"""
import sys, time, random
sys.path.insert(0, "/root/chat-outreach-engine/src")
from chat_outreach_engine.adapters.shopify_contact_form import ShopifyContactFormAdapter
from chat_outreach_engine.pitches import PITCH_A

a = ShopifyContactFormAdapter()
CAP_VIS = """() => { const q=document.querySelectorAll("iframe[src*='hcaptcha'],iframe[title*='captcha' i],.h-captcha,iframe[src*='recaptcha']"); for(const e of q){try{if(e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})&&(e.offsetWidth>80||e.offsetHeight>80))return true;}catch(_){if(e.offsetWidth>80)return true;}} return false; }"""


def one(p, domain):
    b = p.chromium.launch(headless=True, channel=None, args=["--disable-blink-features=AutomationControlled","--no-sandbox"])
    ctx = b.new_context(viewport={"width":1366,"height":900}, locale="en-US",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")
    state = {"post": False}
    def route(r):
        if r.request.method == "POST" and "/contact" in r.request.url:
            state["post"] = True
            try: r.abort()
            except Exception: pass
            return
        try: r.continue_()
        except Exception: pass
    ctx.route("**/*", route)
    page = ctx.new_page()
    v = "no_form"
    try:
        form = a._find_form(page, domain)
        if form is not None:
            a._fill(form, PITCH_A, "noreply@example.com")
            try: form.locator("button[type=submit], input[type=submit]").first.click(timeout=5000, force=True)
            except Exception: pass
            dl = time.time()+12
            while time.time() < dl and not state["post"]:
                time.sleep(0.5)
            if state["post"]:
                v = "captcha_free"
            else:
                try: vis = page.evaluate(CAP_VIS)
                except Exception: vis = False
                v = "captcha_gated" if vis else "unknown"
    except Exception as e:
        v = f"err:{type(e).__name__}"
    b.close()
    return v


def main():
    lst = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv)>2 else 30
    seed = int(sys.argv[3]) if len(sys.argv)>3 else 3
    out = sys.argv[4] if len(sys.argv)>4 else "captcha_free_stores.txt"
    domains = [x.strip() for x in open(lst) if x.strip() and "arova" not in x]
    random.seed(seed); random.shuffle(domains); domains = domains[:n]
    from playwright.sync_api import sync_playwright
    tally = {}; free = []
    with sync_playwright() as p:
        for i, d in enumerate(domains, 1):
            v = one(p, d); tally[v] = tally.get(v,0)+1
            if v == "captcha_free": free.append(d)
            print(f"{i:3}/{n} {d:40} {v}"); sys.stdout.flush()
    with open(out, "w") as f:
        f.write("\n".join(free) + ("\n" if free else ""))
    tot = sum(tally.values())
    print(f"\n== captcha_free {len(free)}/{tot} ({100*len(free)//max(1,tot)}%)  {tally}")
    print(f"== wrote {len(free)} captcha-free domains -> {out}")


if __name__ == "__main__":
    main()
