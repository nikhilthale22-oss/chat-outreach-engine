#!/usr/bin/env python3
"""Gorgias reach + structure probe (NO send). For each store: load, wait for window.GorgiasChat,
open the widget, and report the API surface (sendMessage/open/captureUserEmail/init present) plus
WHERE the conversation renders (which frame, composer + message-container selectors) so the adapter's
delivery-confirm can look in the right place. Calls NO sendMessage - nothing transmits."""
import json, os, sys, time

API_JS = """
() => {
  const g = window.GorgiasChat || null;
  if (!g) return {present:false};
  const t = (k) => { try { return typeof g[k]; } catch(e){ return 'err'; } };
  return {present:true, sendMessage:t('sendMessage'), open:t('open'),
          captureUserEmail:t('captureUserEmail'), init:t('init')};
}
"""
DOM_JS = """
() => {
  const vis = (el) => { try { return el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}); } catch(e){ return !!(el.offsetWidth||el.offsetHeight); } };
  const comps = [];
  for (const el of document.querySelectorAll("textarea,[contenteditable='true']")) {
    if (vis(el)) comps.push({tag:el.tagName.toLowerCase(), ph:(el.getAttribute('placeholder')||el.getAttribute('aria-label')||'').slice(0,40), id:(el.id||'').slice(0,30)});
  }
  // candidate message-list containers (Gorgias renders messages in role=log / [class*=messages])
  const lists = [];
  for (const el of document.querySelectorAll("[role='log'],[class*='message' i],[class*='conversation' i],[data-testid*='message' i]")) {
    if (vis(el)) { const t=(el.innerText||'').trim().slice(0,60); if (t) lists.push(t); }
  }
  return {composers:comps, lists:lists.slice(0,3)};
}
"""


def run(domains, n):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        channel = os.environ.get("BROWSER_CHANNEL", "chrome") or None
        browser = p.chromium.launch(headless=True, channel=channel,
                                    args=["--disable-blink-features=AutomationControlled"])
        live = 0
        for dom in domains[:n]:
            rec = {"domain": dom}
            try:
                ctx = browser.new_context(viewport={"width": 1366, "height": 900}, locale="en-US",
                    user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"))
                page = ctx.new_page()
                page.goto("https://" + dom, wait_until="domcontentloaded", timeout=30000)
                ready = page.evaluate("""async () => { const t0=Date.now();
                    while (Date.now()-t0<15000){ if(window.GorgiasChat) return true;
                    await new Promise(r=>setTimeout(r,300)); } return false; }""")
                rec["ready"] = ready
                if ready:
                    page.evaluate("""async () => { try{ const r=window.GorgiasChat.init&&window.GorgiasChat.init(); if(r&&r.then) await r;}catch(_){}
                        try{ window.GorgiasChat.open&&window.GorgiasChat.open(); }catch(_){}}""")
                    time.sleep(3)
                    rec["api"] = page.evaluate(API_JS)
                    framedump = []
                    for fr in page.frames:
                        if fr == page.main_frame:
                            continue
                        if "gorgias" not in (fr.url or "").lower():
                            continue
                        try:
                            d = fr.evaluate(DOM_JS)
                        except Exception:
                            d = {"composers": [], "lists": []}
                        framedump.append({"url": (fr.url or "")[:70], **d})
                    rec["page_dom"] = page.evaluate(DOM_JS)
                    rec["gorgias_frames"] = framedump
                    if rec["api"].get("sendMessage") == "function":
                        live += 1
                ctx.close()
            except Exception as e:
                rec["error"] = f"{type(e).__name__}: {str(e)[:70]}"
            print(json.dumps(rec)); sys.stdout.flush()
        print(f"\n== sendMessage-live {live}/{min(n,len(domains))} ==")
        browser.close()


if __name__ == "__main__":
    lst = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    domains = [x.strip() for x in open(lst) if x.strip()]
    import random
    random.seed(7); random.shuffle(domains)
    run(domains, n)
