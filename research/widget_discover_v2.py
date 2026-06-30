#!/usr/bin/env python3
"""Discovery harness for new chat-widget vendors (Olark, Freshchat, Zoho SalesIQ, Kustomer,
Richpanel, Gladly, Freshdesk). For each domain: load the store, probe which candidate SDK global
exists, fire candidate open verbs, then dump every VISIBLE composer (textarea / contenteditable) on
the page and inside each iframe, plus iframe URLs. Read the dump to write a VendorConfig.

Usage: python3 widget_discover_v2.py <vendor> <list.txt> [N]
Nothing is typed or sent - this only OPENS widgets and reports DOM. Safe to run unattended.
"""
import json, os, sys, time

VENDORS = {
    "olark": {
        "globals": ["window.olark"],
        "open": "try{olark('api.box.expand')}catch(e){};try{olark('api.box.show')}catch(e){}",
    },
    "freshchat": {
        "globals": ["window.fcWidget", "window.fcWidgetMessengerConfig", "window.freshchat"],
        "open": "try{fcWidget.open()}catch(e){};try{fcWidget.show()}catch(e){}",
    },
    "freshdesk": {
        "globals": ["window.FreshworksWidget", "window.fwSettings", "window.fcWidget"],
        "open": "try{FreshworksWidget('open')}catch(e){};try{fcWidget&&fcWidget.open()}catch(e){}",
    },
    "zoho_salesiq": {
        "globals": ["window.$zoho && window.$zoho.salesiq", "window.$zoho"],
        "open": ("try{$zoho.salesiq.floatwindow.visible('show')}catch(e){};"
                 "try{$zoho.salesiq.floatbutton.visible('show')}catch(e){};"
                 "try{$zoho.salesiq.chat.start()}catch(e){}"),
    },
    "kustomer": {
        "globals": ["window.Kustomer"],
        "open": "try{Kustomer.open()}catch(e){};try{Kustomer.start()}catch(e){}",
    },
    "gladly": {
        "globals": ["window.gladlyChat", "window.Gladly"],
        "open": ("try{gladlyChat.show()}catch(e){};try{gladlyChat.open()}catch(e){};"
                 "try{gladlyChat.toggle()}catch(e){}"),
    },
    "richpanel": {
        "globals": ["window.Richpanel", "window.richpanel", "window.RichpanelWidget"],
        "open": ("try{Richpanel('open')}catch(e){};try{Richpanel('openChat')}catch(e){};"
                 "try{window.richpanel&&richpanel('open')}catch(e){}"),
    },
}

PROBE = """
() => {
  const vis = (el) => { try { return el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}); } catch(e){ return !!(el.offsetWidth||el.offsetHeight); } };
  const desc = (el) => ({
    tag: el.tagName.toLowerCase(),
    type: el.getAttribute('type')||'',
    ph: (el.getAttribute('placeholder')||el.getAttribute('aria-label')||'').slice(0,60),
    id: (el.id||'').slice(0,40),
    name: (el.getAttribute('name')||'').slice(0,40),
  });
  const collect = (root) => {
    const out = [];
    let els = [];
    try { els = Array.from(root.querySelectorAll("textarea, [contenteditable='true'], input[type='text']")); } catch(e){}
    for (const el of els) { if (vis(el)) out.push(desc(el)); }
    return out;
  };
  return { page: collect(document) };
}
"""


def run(vendor, domains, n):
    from playwright.sync_api import sync_playwright
    spec = VENDORS[vendor]
    glob_js = "() => { const r={}; " + "".join(
        f"try{{r[{json.dumps(g)}]=!!({g})}}catch(e){{r[{json.dumps(g)}]=false}};" for g in spec["globals"]
    ) + " return r; }"
    results = []
    with sync_playwright() as p:
        channel = os.environ.get("BROWSER_CHANNEL", "chrome") or None
        browser = p.chromium.launch(headless=True, channel=channel,
                                    args=["--disable-blink-features=AutomationControlled"])
        for dom in domains[:n]:
            rec = {"domain": dom}
            page = None
            try:
                ctx = browser.new_context(
                    viewport={"width": 1366, "height": 900}, locale="en-US",
                    user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"))
                page = ctx.new_page()
                page.goto("https://" + dom, wait_until="domcontentloaded", timeout=40000)
                time.sleep(5)
                rec["globals"] = page.evaluate(glob_js)
                page.evaluate("() => { try { " + spec["open"] + "; } catch(_){} }")
                time.sleep(4)
                rec["page_composers"] = page.evaluate(PROBE)["page"]
                frames = []
                for fr in page.frames:
                    if fr == page.main_frame:
                        continue
                    try:
                        comps = fr.evaluate(PROBE)["page"]
                    except Exception:
                        comps = []
                    if comps or any(k in (fr.url or "") for k in
                                    ["olark", "freshchat", "freshworks", "zoho", "salesiq",
                                     "kustomer", "gladly", "richpanel", "freshdesk", "wchat"]):
                        frames.append({"url": (fr.url or "")[:90], "composers": comps})
                rec["frames"] = frames
                ctx.close()
            except Exception as e:
                rec["error"] = f"{type(e).__name__}: {str(e)[:90]}"
                try:
                    if page: page.context.close()
                except Exception:
                    pass
            results.append(rec)
            print(json.dumps(rec))
            sys.stdout.flush()
        browser.close()
    return results


if __name__ == "__main__":
    vendor = sys.argv[1]
    lst = sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    with open(lst) as f:
        domains = [x.strip() for x in f if x.strip()]
    run(vendor, domains, n)
