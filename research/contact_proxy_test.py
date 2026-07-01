#!/usr/bin/env python3
"""The pivotal test: Shopify's native contact form is gated by the SAME hCaptcha as Shopify Inbox
(invisible at load, fires on submit). Does the residential proxy make it PASS? Submit the Arova mock
store contact form DIRECT vs THROUGH THE PROXY and report: delivered / hcaptcha_challenge / no_post."""
import os, time, sys
sys.path.insert(0, "/root/chat-outreach-engine/src")
from chat_outreach_engine.adapters.shopify_contact_form import ShopifyContactFormAdapter
from chat_outreach_engine.pitches import PITCH_A

DOMAIN = "arova-5265.myshopify.com"
a = ShopifyContactFormAdapter()
from playwright.sync_api import sync_playwright

CAPTCHA_JS = """() => !!document.querySelector("iframe[src*='hcaptcha'], iframe[title*='captcha' i], .h-captcha, [id*='hcaptcha']")"""


def load_proxy_env():
    env = {}
    try:
        with open("/root/chat-outreach-engine/.env.proxy") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1); env[k] = v
    except FileNotFoundError:
        pass
    return env


def run(mode):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, channel=None, args=["--disable-blink-features=AutomationControlled"])
        proxy = None
        if mode == "proxy":
            e = load_proxy_env()
            host = e["PROXY_SERVER"].split("://",1)[1]
            proxy = {"server": e["PROXY_SERVER"], "username": e["PROXY_USERNAME"], "password": e["PROXY_PASSWORD"]}
        page = b.new_context(viewport={"width":1366,"height":900}, locale="en-US", proxy=proxy).new_page()
        form = a._find_form(page, DOMAIN)
        if form is None:
            print(f"[{mode}] no form (load blocked?)"); b.close(); return
        a._fill(form, PITCH_A, "nikhilthale18@gmail.com")
        before = page.url
        try:
            form.locator("button[type=submit], input[type=submit]").first.click(timeout=5000, force=True)
        except Exception as ex:
            print(f"[{mode}] click err {ex}"); b.close(); return
        time.sleep(6)
        after = page.url
        body = page.evaluate("() => document.body.innerText||''").lower()
        captcha = page.evaluate(CAPTCHA_JS)
        delivered = "contact_posted=true" in after or "thank" in body or "get back" in body or "received" in body
        verdict = "DELIVERED" if delivered else ("hcaptcha_challenge" if captcha else ("no_post(url_same)" if before==after else "unknown"))
        print(f"[{mode}] verdict={verdict}  url_changed={before!=after}  captcha_present={captcha}  after={after[:60]}")
        b.close()


if __name__ == "__main__":
    run("direct")
    run("proxy")
