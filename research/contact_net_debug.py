#!/usr/bin/env python3
"""Does the Arova contact submit fire a POST at all? Capture all requests/responses to /contact and
report method+status, plus any console errors. Screenshot the final state."""
import time, sys
sys.path.insert(0, "/root/chat-outreach-engine/src")
from chat_outreach_engine.adapters.shopify_contact_form import ShopifyContactFormAdapter
from chat_outreach_engine.pitches import PITCH_A

DOMAIN = "arova-5265.myshopify.com"
a = ShopifyContactFormAdapter()
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, channel=None, args=["--disable-blink-features=AutomationControlled"])
    page = b.new_context(viewport={"width":1366,"height":900}, locale="en-US").new_page()
    reqs, cons = [], []
    page.on("request", lambda r: reqs.append((r.method, r.url)) if "/contact" in r.url else None)
    page.on("response", lambda r: reqs.append(("RESP "+str(r.status), r.url)) if "/contact" in r.url and r.request.method == "POST" else None)
    page.on("console", lambda m: cons.append(m.type + ":" + m.text[:80]) if m.type in ("error","warning") else None)

    form = a._find_form(page, DOMAIN)
    a._fill(form, PITCH_A, "nikhilthale18@gmail.com")
    # check HTML5 validity + any onsubmit listener presence
    valid = form.evaluate("f => f.checkValidity()")
    print("form.checkValidity():", valid)
    invalids = form.evaluate("f => Array.from(f.querySelectorAll(':invalid')).map(e => (e.getAttribute('name')||e.tagName)+' '+ (e.validationMessage||''))")
    print("invalid fields:", invalids)

    btn = form.locator("button[type=submit]").first
    try:
        btn.click(timeout=5000, force=True)
    except Exception as e:
        print("click err:", e)
    time.sleep(5)
    print("url:", page.url)
    print("/contact requests:", reqs)
    print("console errs:", cons[:6])
    body = page.evaluate("() => document.body.innerText||''")
    import re
    print("signal lines:", [l.strip() for l in body.splitlines() if re.search(r'thank|sent|error|required|received|get back|invalid|valid', l, re.I)][:8])
    page.screenshot(path="/tmp/arova_net.png", full_page=False)
    b.close()
