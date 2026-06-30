#!/usr/bin/env python3
"""Deeper re-probe for vendors whose SDK global is live but whose composer did not surface on the
first pass (Kustomer, Richpanel). Tries several open verbs, waits longer, and dumps EVERY iframe
(url + visible composer count), unfiltered, so a composer iframe with an unexpected URL is not missed.
Nothing is typed or sent."""
import json, os, sys, time

VERBS = {
    "kustomer": [
        "try{Kustomer.open()}catch(e){}",
        "try{Kustomer.start()}catch(e){}",
        "try{Kustomer.open({}, ()=>{})}catch(e){}",
        "try{document.querySelector('iframe[data-cy=\\'kustomer-launcher-frame\\'],iframe[title*=\\'hat\\' i]')}catch(e){}",
    ],
    "richpanel": [
        "try{Richpanel('open')}catch(e){}",
        "try{Richpanel('openMessenger')}catch(e){}",
        "try{Richpanel('show')}catch(e){}",
        "try{Richpanel('maximize')}catch(e){}",
        "try{richpanel('open')}catch(e){}",
    ],
    "freshchat": [
        "try{fcWidget.open()}catch(e){};try{fcWidget.show()}catch(e){}",
        "try{window.fcWidget&&window.fcWidget.open()}catch(e){}",
    ],
}
GLOBALS = {
    "kustomer": ["window.Kustomer"],
    "richpanel": ["window.Richpanel", "window.richpanel"],
    "freshchat": ["window.fcWidget", "window.fcWidgetMessengerConfig", "window.fcSettings", "window.fcWidget && window.fcWidget.isInitialized && window.fcWidget.isInitialized()"],
}
PROBE = """
() => {
  const vis = (el) => { try { return el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}); } catch(e){ return !!(el.offsetWidth||el.offsetHeight); } };
  const out = [];
  let els = [];
  try { els = Array.from(document.querySelectorAll("textarea, [contenteditable='true'], input[type='text']")); } catch(e){}
  for (const el of els) { if (vis(el)) out.push({tag: el.tagName.toLowerCase(), ph:(el.getAttribute('placeholder')||el.getAttribute('aria-label')||'').slice(0,50), id:(el.id||'').slice(0,40)}); }
  return out;
}
"""

def run(vendor, domains, n):
    from playwright.sync_api import sync_playwright
    glob_js = "() => { const r={}; " + "".join(
        f"try{{r[{json.dumps(g)}]=!!({g})}}catch(e){{r[{json.dumps(g)}]=false}};" for g in GLOBALS[vendor]
    ) + " return r; }"
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
                page.goto("https://" + dom, wait_until="domcontentloaded", timeout=40000)
                time.sleep(5)
                rec["globals"] = page.evaluate(glob_js)
                for verb in VERBS[vendor]:
                    page.evaluate("() => { try { " + verb + "; } catch(_){} }")
                    time.sleep(1.5)
                time.sleep(4)
                rec["page"] = page.evaluate(PROBE)
                frames = []
                for fr in page.frames:
                    if fr == page.main_frame:
                        continue
                    try:
                        comps = fr.evaluate(PROBE)
                    except Exception:
                        comps = []
                    frames.append({"url": (fr.url or "")[:80], "n": len(comps),
                                   "comp": comps[:2]})
                rec["frames"] = frames
                ctx.close()
            except Exception as e:
                rec["error"] = f"{type(e).__name__}: {str(e)[:80]}"
            print(json.dumps(rec)); sys.stdout.flush()
        browser.close()

if __name__ == "__main__":
    vendor, lst = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    with open(lst) as f:
        domains = [x.strip() for x in f if x.strip()]
    run(vendor, domains, n)
