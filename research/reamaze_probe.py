#!/usr/bin/env python3
"""Re:amaze menu-flow probe. popup() opens a MENU (not the composer); the composer is behind an entry
click, inside an about:blank frame. This finds: (1) which frame holds the menu + a STABLE container
marker present at menu stage (to resolve the about:blank frame BEFORE the composer exists), (2) the
visible entry texts (to pick the entry label), then clicks the best entry and reports whether the
composer appears. No send."""
import json, os, sys, time

DUMP = """
() => {
  const vis = (el) => { try { return el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}); } catch(e){ return !!(el.offsetWidth||el.offsetHeight); } };
  const click_texts = [];
  for (const el of document.querySelectorAll("a,button,[role='button'],[class*='item' i],[class*='channel' i],[class*='option' i]")) {
    if (vis(el)) { const t=(el.innerText||'').trim(); if (t && t.length<40) click_texts.push(t); }
  }
  const comps = [];
  for (const el of document.querySelectorAll("textarea,[contenteditable='true']")) {
    if (vis(el)) comps.push({ph:(el.getAttribute('placeholder')||el.getAttribute('aria-label')||'').slice(0,40), id:(el.id||'').slice(0,30)});
  }
  // candidate stable containers (present at menu stage): elements with a reamaze-ish class/id
  const markers = [];
  for (const el of document.querySelectorAll("[class*='reamaze' i],[id*='reamaze' i],[class*='cs-' i],[id*='cs-' i]")) {
    const sel = el.id ? ('#'+el.id) : (el.className && typeof el.className==='string' ? '.'+el.className.split(' ')[0] : '');
    if (sel) markers.push(sel.slice(0,40));
  }
  return {clicks:[...new Set(click_texts)].slice(0,12), composers:comps, markers:[...new Set(markers)].slice(0,6)};
}
"""

ENTRY_LABELS = ["send us a message", "send a message", "contact us directly", "start a conversation",
                "new conversation", "message us", "chat", "email us"]


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
                page.goto("https://" + dom, wait_until="domcontentloaded", timeout=35000)
                ready = page.evaluate("""async()=>{const t0=Date.now();while(Date.now()-t0<18000){if(window.Reamaze)return true;await new Promise(r=>setTimeout(r,300));}return false;}""")
                rec["reamaze"] = ready
                if not ready:
                    rec["note"] = "no_reamaze_global"; print(json.dumps(rec)); ctx.close(); continue
                page.evaluate("()=>{try{window.Reamaze&&Reamaze.popup&&Reamaze.popup()}catch(_){}}")
                time.sleep(4)
                # find the menu frame (about:blank or reamaze url) that has clickable entries
                menu_fr = None; menu_dump = None
                for fr in page.frames:
                    if fr == page.main_frame:
                        continue
                    try:
                        d = fr.evaluate(DUMP)
                    except Exception:
                        continue
                    if d["clicks"] or d["composers"]:
                        menu_fr = fr; menu_dump = d
                        rec["menu_frame"] = (fr.url or "")[:50]; rec["menu_stage"] = d
                        break
                if menu_fr is None:
                    rec["note"] = "no_menu_frame"; print(json.dumps(rec)); ctx.close(); continue
                # click the best entry by label
                clicked = None
                for label in ENTRY_LABELS:
                    try:
                        loc = menu_fr.get_by_text(label, exact=False).first
                        if loc.count() and loc.is_visible(timeout=800):
                            loc.click(timeout=2500); clicked = label; break
                    except Exception:
                        continue
                rec["clicked_entry"] = clicked
                time.sleep(3)
                # re-scan for a composer across all frames
                comp_hit = None
                for fr in page.frames:
                    try:
                        d = fr.evaluate(DUMP)
                    except Exception:
                        continue
                    if d["composers"]:
                        comp_hit = {"frame": (fr.url or "")[:50] or "(main)", "composers": d["composers"]}
                        break
                rec["after_click_composer"] = comp_hit
                ctx.close()
            except Exception as e:
                rec["error"] = f"{type(e).__name__}: {str(e)[:60]}"
            print(json.dumps(rec)); sys.stdout.flush()
        browser.close()


if __name__ == "__main__":
    lst = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    domains = [x.strip() for x in open(lst) if x.strip()]
    import random
    random.seed(5); random.shuffle(domains)
    run(domains, n)
