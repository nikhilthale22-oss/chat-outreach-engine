#!/usr/bin/env python3
"""Does a HEADED browser beat Shopify's contact-form hCaptcha where headless does not? Same submit,
headless vs headed (direct, no proxy - isolates the browser-fingerprint effect). Robust: poll up to
12s for a POST to /contact (= hCaptcha passed), abort it so NOTHING is sent. No resource blocking (that
caused false no_form earlier). Run under: xvfb-run -a .venv/bin/python research/measure_contact_headed.py

Usage: xvfb-run -a python research/measure_contact_headed.py <list.txt> [N] [seed]
"""
import sys, time, random
sys.path.insert(0, "/root/chat-outreach-engine/src")
from chat_outreach_engine.adapters.shopify_contact_form import ShopifyContactFormAdapter
from chat_outreach_engine.pitches import PITCH_A

a = ShopifyContactFormAdapter()
CAPTCHA_VIS_JS = """() => {
  const els = document.querySelectorAll("iframe[src*='hcaptcha'], iframe[title*='captcha' i], .h-captcha, iframe[src*='recaptcha']");
  for (const e of els) { try { if (e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}) && (e.offsetWidth>80||e.offsetHeight>80)) return true; } catch(_){ if (e.offsetWidth>80) return true; } }
  return false;
}"""


def one(p, domain, headed):
    b = p.chromium.launch(headless=not headed, channel=None,
                          args=["--disable-blink-features=AutomationControlled",
                                "--no-sandbox"] + (["--start-maximized"] if headed else []))
    ctx = b.new_context(viewport={"width":1366,"height":900}, locale="en-US",
        user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"))
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
    verdict = "no_form"
    try:
        form = a._find_form(page, domain)
        if form is not None:
            a._fill(form, PITCH_A, "noreply@example.com")
            try:
                form.locator("button[type=submit], input[type=submit]").first.click(timeout=5000, force=True)
            except Exception:
                pass
            deadline = time.time() + 12
            while time.time() < deadline and not state["post"]:
                time.sleep(0.5)
            if state["post"]:
                verdict = "would_pass"
            else:
                try: vis = page.evaluate(CAPTCHA_VIS_JS)
                except Exception: vis = False
                verdict = "challenged" if vis else "no_submit"
    except Exception as e:
        verdict = f"err:{type(e).__name__}"
    b.close()
    return verdict


def main():
    lst = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 9
    domains = [x.strip() for x in open(lst) if x.strip() and "arova" not in x]
    random.seed(seed); random.shuffle(domains); domains = domains[:n]
    from playwright.sync_api import sync_playwright
    tally = {"headless": {}, "headed": {}}
    with sync_playwright() as p:
        for d in domains:
            vhl = one(p, d, headed=False)
            vhd = one(p, d, headed=True)
            tally["headless"][vhl] = tally["headless"].get(vhl, 0) + 1
            tally["headed"][vhd] = tally["headed"].get(vhd, 0) + 1
            print(f"{d:38} headless={vhl:11} headed={vhd:11}")
            sys.stdout.flush()
    for m in ("headless", "headed"):
        t = tally[m]; tot = sum(t.values()); wp = t.get("would_pass", 0)
        print(f"\n== {m}: would_pass {wp}/{tot} ({100*wp//max(1,tot)}%)  {t}")


if __name__ == "__main__":
    main()
