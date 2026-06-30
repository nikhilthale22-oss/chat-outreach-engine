#!/usr/bin/env python3
"""Re-qualify the Gorgias pool to CHAT-LIVE stores. The StoreLeads 'Gorgias' tag flags the Gorgias
helpdesk/contact-forms platform; most such stores expose only window.GorgiasBridge (bundle-loader)
and use Gorgias for email, with the on-site CHAT widget OFF. The adapter can only drive the chat
(window.GorgiasChat). This scans a random sample, waits up to 20s for GorgiasChat, and reports the
true chat-live rate + writes the live domains. No send."""
import json, os, sys, time

WAIT_MS = int(os.environ.get("GORGIAS_WAIT_MS", "20000"))
CHECK = ("""
async () => {
  const t0 = Date.now();
  while (Date.now() - t0 < %d) {""" % WAIT_MS) + """
    if (window.GorgiasChat) {
      let sm='no'; try { sm = typeof window.GorgiasChat.sendMessage; } catch(e){ sm='err'; }
      return {chat:true, sendMessage:sm};
    }
    await new Promise(r => setTimeout(r, 400));
  }
  return {chat:false, bridge: (typeof window.GorgiasBridge !== 'undefined')};
}
"""


def run(domains, n, out_path):
    from playwright.sync_api import sync_playwright
    live = []
    bridge_only = 0
    no_gorgias = 0
    errors = 0
    with sync_playwright() as p:
        channel = os.environ.get("BROWSER_CHANNEL", "chrome") or None
        browser = p.chromium.launch(headless=True, channel=channel,
                                    args=["--disable-blink-features=AutomationControlled"])
        for i, dom in enumerate(domains[:n], 1):
            tag = "?"
            try:
                ctx = browser.new_context(viewport={"width": 1366, "height": 900}, locale="en-US",
                    user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"))
                page = ctx.new_page()
                page.goto("https://" + dom, wait_until="domcontentloaded", timeout=30000)
                r = page.evaluate(CHECK)
                if r.get("chat"):
                    live.append(dom); tag = f"CHAT-LIVE sendMessage={r.get('sendMessage')}"
                elif r.get("bridge"):
                    bridge_only += 1; tag = "bridge-only (helpdesk/contact-forms, chat OFF)"
                else:
                    no_gorgias += 1; tag = "no-gorgias (stale/blocked)"
                ctx.close()
            except Exception as e:
                errors += 1; tag = f"ERR {type(e).__name__}"
            print(f"{i:3}/{n}  {dom:40} {tag}"); sys.stdout.flush()
        browser.close()
    with open(out_path, "w") as f:
        f.write("\n".join(live) + ("\n" if live else ""))
    print(f"\n== CHAT-LIVE {len(live)}/{n}  |  bridge-only {bridge_only}  no-gorgias {no_gorgias}  err {errors} ==")
    print(f"== wrote {len(live)} chat-live domains -> {out_path} ==")


if __name__ == "__main__":
    lst = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    out_path = sys.argv[3] if len(sys.argv) > 3 else "gorgias_chatlive.txt"
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 11
    domains = [x.strip() for x in open(lst) if x.strip()]
    import random
    random.seed(seed); random.shuffle(domains)
    run(domains, n, out_path)
