#!/usr/bin/env python3
"""Launcher-click discovery for vendors whose SDK global is LIVE but whose composer does not surface
from a JS open() headless (Kustomer, Richpanel) or that hide it behind a menu/entry (Re:amaze, Zoho).

For each store: confirm the global, try the JS open verb, then if no composer surfaced, find the
floating LAUNCHER (a visible clickable in the bottom-right corner, in the page or in any frame -
launchers are often their own iframe) and CLICK it, then re-scan every frame for a visible composer.
Reports which path reached a composer + the composer's frame url + selector, so a VendorConfig (and a
generic launcher_selector capability) can be written. Nothing is typed or sent.

Usage: python3 research/launcher_discover.py <vendor> <list.txt> [N]
"""
import json, os, sys, time

VENDORS = {
    "richpanel": {"globals": ["window.Richpanel", "window.richpanel"],
                  "open": "try{Richpanel('open')}catch(e){};try{Richpanel('openMessenger')}catch(e){}",
                  "frame_hint": "richpanel"},
    "kustomer": {"globals": ["window.Kustomer"],
                 "open": "try{Kustomer.open()}catch(e){};try{Kustomer.start()}catch(e){}",
                 "frame_hint": "kustomer"},
    "reamaze": {"globals": ["window.Reamaze", "window._support"],
                "open": "try{window.Reamaze&&Reamaze.popup&&Reamaze.popup()}catch(e){}",
                "frame_hint": "reamaze"},
    "zoho-salesiq": {"globals": ["window.$zoho && window.$zoho.salesiq"],
                     "open": ("try{$zoho.salesiq.floatwindow.visible('show')}catch(e){};"
                              "try{$zoho.salesiq.chat.start()}catch(e){}"),
                     "frame_hint": "zoho"},
}

# find a visible composer anywhere; return [{frame, selector, ph}]
SCAN = """
() => {
  const vis = (el) => { try { return el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}); } catch(e){ return !!(el.offsetWidth||el.offsetHeight); } };
  const out = [];
  for (const el of document.querySelectorAll("textarea, [contenteditable='true']")) {
    if (vis(el)) out.push({tag: el.tagName.toLowerCase(), ph:(el.getAttribute('placeholder')||el.getAttribute('aria-label')||'').slice(0,40), id:(el.id||'').slice(0,30)});
  }
  return out;
}
"""

# launcher candidates: visible clickable in the bottom-right corner OR with chat-ish attributes
LAUNCH_CANDIDATES = """
() => {
  const W = window.innerWidth, H = window.innerHeight;
  const vis = (el) => { try { return el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}); } catch(e){ return !!(el.offsetWidth||el.offsetHeight); } };
  const chatish = (s) => /chat|messenger|launcher|help|support|widget|bubble|open/i.test(s||'');
  const out = [];
  const els = Array.from(document.querySelectorAll("button,[role='button'],a,div[class*='launch' i],div[class*='button' i]"));
  for (let i=0;i<els.length;i++){
    const el = els[i];
    if (!vis(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 8 || r.width > 250 || r.height > 250) continue;
    const bottomRight = (W - r.right) < 160 && (H - r.bottom) < 200;
    const attrs = (el.getAttribute('aria-label')||'')+' '+(el.className||'')+' '+(el.id||'')+' '+(el.getAttribute('title')||'');
    if (bottomRight || chatish(attrs)) {
      out.push({idx:i, br:bottomRight, aria:(el.getAttribute('aria-label')||'').slice(0,30), cls:String(el.className||'').slice(0,40)});
    }
  }
  return out.slice(0, 8);
}
"""


def scan_all(page):
    """Return list of (frame_url, composers) for frames that have a visible composer."""
    hits = []
    for fr in page.frames:
        try:
            comps = fr.evaluate(SCAN)
        except Exception:
            comps = []
        if comps:
            hits.append({"frame": (fr.url or "")[:70] or "(main)", "composers": comps[:2]})
    return hits


def click_launchers(page, frame_hint):
    """Try clicking launcher candidates in the page and in vendor frames. Returns the click that
    surfaced a composer, or None."""
    surfaces = [("(page)", page.main_frame)]
    for fr in page.frames:
        if fr != page.main_frame and frame_hint in (fr.url or "").lower():
            surfaces.append(((fr.url or "")[:50], fr))
    # also any frame that looks like a launcher (small, vendor)
    for where, fr in surfaces:
        try:
            cands = fr.evaluate(LAUNCH_CANDIDATES)
        except Exception:
            cands = []
        for c in cands:
            try:
                loc = fr.locator("button,[role='button'],a,div[class*='launch' i],div[class*='button' i]").nth(c["idx"])
                loc.click(timeout=2500, force=True)
            except Exception:
                continue
            time.sleep(2.5)
            hits = scan_all(page)
            if hits:
                return {"clicked_in": where, "cand": c, "composer": hits[0]}
    return None


def run(vendor, domains, n):
    from playwright.sync_api import sync_playwright
    spec = VENDORS[vendor]
    glob_js = "() => { const r={}; " + "".join(
        f"try{{r['{g}']=!!({g})}}catch(e){{r['{g}']=false}};" for g in spec["globals"]) + " return r; }"
    with sync_playwright() as p:
        channel = os.environ.get("BROWSER_CHANNEL", "chrome") or None
        browser = p.chromium.launch(headless=True, channel=channel,
                                    args=["--disable-blink-features=AutomationControlled"])
        reached = 0
        for dom in domains[:n]:
            rec = {"domain": dom}
            try:
                ctx = browser.new_context(viewport={"width": 1366, "height": 900}, locale="en-US",
                    user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"))
                page = ctx.new_page()
                page.goto("https://" + dom, wait_until="domcontentloaded", timeout=35000)
                time.sleep(5)
                rec["globals"] = page.evaluate(glob_js)
                page.evaluate("() => { try { " + spec["open"] + "; } catch(_){} }")
                time.sleep(3)
                hits = scan_all(page)
                if hits:
                    rec["path"] = "js_open"; rec["composer"] = hits[0]; reached += 1
                else:
                    res = click_launchers(page, spec["frame_hint"])
                    if res:
                        rec["path"] = "launcher_click"; rec.update(res); reached += 1
                    else:
                        rec["path"] = "no_composer"
                ctx.close()
            except Exception as e:
                rec["path"] = "error"; rec["error"] = f"{type(e).__name__}: {str(e)[:60]}"
            print(json.dumps(rec)); sys.stdout.flush()
        print(f"\n== {vendor}: composer reached {reached}/{min(n,len(domains))} ==")
        browser.close()


if __name__ == "__main__":
    vendor, lst = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    domains = [x.strip() for x in open(lst) if x.strip()]
    import random
    random.seed(5); random.shuffle(domains)
    run(vendor, domains, n)
