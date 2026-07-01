#!/usr/bin/env python3
"""Isolate the Arova contact-form SUBMIT: dump the submit controls in the form, then try submit
strategies one at a time and report which one navigates to contact_posted=true."""
import time, sys
sys.path.insert(0, "/root/chat-outreach-engine/src")
from chat_outreach_engine.adapters.shopify_contact_form import ShopifyContactFormAdapter
from chat_outreach_engine.pitches import PITCH_A

DOMAIN = "arova-5265.myshopify.com"
a = ShopifyContactFormAdapter()
from playwright.sync_api import sync_playwright


def fresh(p):
    b = p.chromium.launch(headless=True, channel=None, args=["--disable-blink-features=AutomationControlled"])
    page = b.new_context(viewport={"width":1366,"height":900}, locale="en-US").new_page()
    form = a._find_form(page, DOMAIN)
    a._fill(form, PITCH_A, "nikhilthale18@gmail.com")
    return b, page, form


with sync_playwright() as p:
    # dump submit controls
    b, page, form = fresh(p)
    ctrls = form.evaluate("""f => Array.from(f.querySelectorAll('button, input[type=submit]')).map(e => ({tag:e.tagName.toLowerCase(), type:e.getAttribute('type')||'', text:(e.innerText||e.value||'').slice(0,20), visible:!!(e.offsetWidth||e.offsetHeight)}))""")
    print("submit controls in form:", ctrls)
    action = form.evaluate("f => f.getAttribute('action')")
    print("form action:", action)
    b.close()

    for strat in ["button_click", "requestSubmit", "submit", "enter_textarea"]:
        b, page, form = fresh(p)
        before = page.url
        try:
            if strat == "button_click":
                form.locator("button[type=submit], input[type=submit], button:has-text('Send'), button:has-text('Submit')").first.click(timeout=5000, force=True)
            elif strat == "requestSubmit":
                form.evaluate("f => f.requestSubmit ? f.requestSubmit() : f.submit()")
            elif strat == "submit":
                form.evaluate("f => f.submit()")
            elif strat == "enter_textarea":
                form.locator("textarea").first.press("Enter")
        except Exception as e:
            print(f"[{strat}] error: {type(e).__name__} {str(e)[:60]}")
            b.close(); continue
        time.sleep(4)
        after = page.url
        body = page.evaluate("() => document.body.innerText || ''").lower()
        ok = "contact_posted=true" in after or "thank" in body or "get back" in body or "received" in body
        print(f"[{strat}] url_changed={before!=after} success={ok} after={after[:70]}")
        b.close()
