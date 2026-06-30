#!/usr/bin/env python3
"""Why did window.GorgiasChat never load? For each store dump: page title (did it render or get
blocked), any window key matching /gorgia/i, any <script src> containing gorgias, any iframe whose
url contains gorgias, and re-check window.GorgiasChat after a LONGER wait. No send."""
import json, os, sys, time

DIAG = """
() => {
  const keys = Object.keys(window).filter(k => /gorgia/i.test(k));
  const scripts = Array.from(document.scripts).map(s=>s.src).filter(s=>/gorgias/i.test(s)).slice(0,4);
  const iframes = Array.from(document.querySelectorAll('iframe')).map(f=>f.src||f.getAttribute('src')||'').filter(s=>/gorgias/i.test(s)).slice(0,4);
  return {title: document.title.slice(0,50), gorgiaKeys: keys.slice(0,8),
          gorgiasScripts: scripts, gorgiasIframes: iframes,
          hasGorgiasChat: typeof window.GorgiasChat,
          gorgiasChatKeys: window.GorgiasChat ? Object.keys(window.GorgiasChat).slice(0,12) : []};
}
"""


def run(domains, n):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        channel = os.environ.get("BROWSER_CHANNEL", "chrome") or None
        browser = p.chromium.launch(headless=True, channel=channel,
                                    args=["--disable-blink-features=AutomationControlled"])
        for dom in domains[:n]:
            rec = {"domain": dom}
            try:
                ctx = browser.new_context(viewport={"width": 1366, "height": 900}, locale="en-US",
                    user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"))
                page = ctx.new_page()
                page.goto("https://" + dom, wait_until="load", timeout=35000)
                time.sleep(8)
                # nudge lazy loaders: scroll + mousemove (some widgets boot on first interaction)
                try:
                    page.mouse.move(700, 400); page.evaluate("window.scrollTo(0, 600)")
                except Exception:
                    pass
                time.sleep(4)
                rec.update(page.evaluate(DIAG))
                ctx.close()
            except Exception as e:
                rec["error"] = f"{type(e).__name__}: {str(e)[:70]}"
            print(json.dumps(rec)); sys.stdout.flush()
        browser.close()


if __name__ == "__main__":
    lst = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    domains = [x.strip() for x in open(lst) if x.strip()]
    import random
    random.seed(7); random.shuffle(domains)
    run(domains, n)
