#!/usr/bin/env python3
"""Run ON Server #1. Confirms CHROMIUM (the engine's actual browser, via the engine's playwright_proxy())
honors the ProxyBase auth - the real integration risk. Loads an IP-echo page through the proxy and
prints the egress IP. Tiny bandwidth. No credentials printed."""
import os

# load .env.proxy into the environment, exactly as a real engine run would
with open("/root/chat-outreach-engine/.env.proxy") as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1); os.environ[k] = v

import sys
sys.path.insert(0, "/root/chat-outreach-engine/src")
from chat_outreach_engine.proxy import playwright_proxy

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel=None,
                                args=["--disable-blink-features=AutomationControlled"])
    page = browser.new_context(proxy=playwright_proxy()).new_page()
    try:
        page.goto("https://api.ipify.org?format=json", wait_until="domcontentloaded", timeout=40000)
        print("chromium-through-proxy egress:", page.evaluate("() => document.body.innerText")[:120])
        print("OK - Chromium honors ProxyBase auth")
    except Exception as e:
        print("CHROMIUM PROXY FAILED:", type(e).__name__, str(e)[:160])
    finally:
        browser.close()
