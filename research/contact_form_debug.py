#!/usr/bin/env python3
"""Debug the Arova contact-form submit: find the form, fill it, submit, then dump url before/after,
whether the form is still present, any success/error text, and a screenshot. No proxy."""
import os, time, sys

sys.path.insert(0, "/root/chat-outreach-engine/src")
from chat_outreach_engine.adapters.shopify_contact_form import ShopifyContactFormAdapter
from chat_outreach_engine.pitches import PITCH_A

DOMAIN = "arova-5265.myshopify.com"
a = ShopifyContactFormAdapter()

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, channel=None, args=["--disable-blink-features=AutomationControlled"])
    page = b.new_context(viewport={"width":1366,"height":900}, locale="en-US").new_page()
    form = a._find_form(page, DOMAIN)
    print("form found:", form is not None, "| url:", page.url)
    if form is not None:
        print("captcha:", a._has_captcha(form))
        # show the field roles
        fields = form.evaluate("""f => Array.from(f.querySelectorAll('input,textarea,select')).map(e => ({tag:e.tagName.toLowerCase(), name:e.getAttribute('name')||'', type:e.getAttribute('type')||'', required:e.required, visible: !!(e.offsetWidth||e.offsetHeight)}))""")
        print("fields:", fields)
        filled = a._fill(form, PITCH_A, "nikhilthale18@gmail.com")
        print("fill ok:", filled)
        # values after fill
        vals = form.evaluate("""f => Array.from(f.querySelectorAll('input,textarea')).map(e => (e.getAttribute('name')||e.type)+'='+String(e.value||'').slice(0,20))""")
        print("values:", vals)
        before = page.url
        a._submit(form, page)
        time.sleep(4)
        after = page.url
        print("url before:", before)
        print("url after :", after, "| changed:", before != after)
        body = page.evaluate("() => (document.body && document.body.innerText || '')")
        # print lines mentioning thank/sent/error/required/success
        import re
        hits = [l.strip() for l in body.splitlines() if re.search(r'thank|sent|success|error|required|received|get back', l, re.I)]
        print("signal lines:", hits[:8])
        still_form = page.locator("form textarea").count()
        print("textarea still on page:", still_form)
        try:
            page.screenshot(path="/tmp/arova_contact_after.png")
            print("screenshot -> /tmp/arova_contact_after.png")
        except Exception as e:
            print("shot fail", e)
    b.close()
