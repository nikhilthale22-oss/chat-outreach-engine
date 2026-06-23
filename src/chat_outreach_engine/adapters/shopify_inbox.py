"""ShopifyInboxAdapter: Adapter for the Shopify Inbox storefront chat.

Shopify Inbox has NO JS API. The widget is an <inbox-online-store-chat> custom element
with an OPEN shadow DOM exposing stable data-spec selectors (Playwright locators pierce
open shadow roots automatically):
    launcher   [data-spec="toggle-button"]
    composer   textarea[data-spec="message-input"]
    send        button[data-spec="message-submit"]
The email gate (customer-info form) appears AFTER the first message is sent; we fill the
reply email there so the merchant's reply comes back to us by email (research/reply-delivery.md).

KNOWN LIMITATION (verified 2026-06-23): that customer-info form is CAPTCHA-gated
(g-recaptcha-response + h-captcha-response), so a new-visitor message does NOT deliver
without solving the CAPTCHA. This adapter opens/types/sends and fills the email, but cannot
pass the CAPTCHA - so Shopify Inbox is currently NOT a reliable automated channel. Kept for
reference / future use with a captcha-solving service. See research/shopify-inbox-injection.md.

Env:
    HEADED=1    show a real Chrome window
    SI_DEBUG=1  save phase screenshots to /tmp/si_dbg_*.png
"""
from __future__ import annotations

import os
import time

from ..injector import SendResult

LAUNCH = '[data-spec="toggle-button"]'
COMPOSER = 'textarea[data-spec="message-input"]'
SEND = 'button[data-spec="message-submit"]'
EMAIL_SELECTORS = ['input[type="email"]', '[data-spec*="email"]',
                   'input[name*="email"]', 'input[placeholder*="mail"]']
SUBMIT_SELECTORS = ['button[type="submit"]', '[data-spec*="submit"]', '[data-spec*="email"] button']


class ShopifyInboxAdapter:
    vendor = "shopify-inbox"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        from playwright.sync_api import sync_playwright

        headed = os.environ.get("HEADED", "").lower() in ("1", "true", "yes")
        debug = bool(os.environ.get("SI_DEBUG"))
        url = "https://" + domain

        def shot(page, name):
            if debug:
                try:
                    page.screenshot(path=f"/tmp/si_dbg_{name}.png")
                except Exception:
                    pass

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=not headed, channel="chrome",
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = browser.new_context(
                viewport={"width": 1366, "height": 900}, locale="en-US"
            ).new_page()
            try:
                page.goto(url, wait_until="load", timeout=30000)
                page.wait_for_timeout(7000)
                try:
                    page.keyboard.press("Escape")  # dismiss marketing popups
                except Exception:
                    pass
                page.wait_for_timeout(500)

                try:
                    page.locator(LAUNCH).first.click(timeout=8000)
                except Exception as e:
                    return SendResult(False, f"no_launcher: {str(e)[:80]}")
                shot(page, "1_opened")

                try:
                    composer = page.locator(COMPOSER).first
                    composer.wait_for(state="visible", timeout=10000)
                except Exception:
                    return SendResult(False, "no_composer")

                composer.fill(pitch)
                time.sleep(0.5)
                shot(page, "2_typed")

                try:
                    page.locator(SEND).first.click(timeout=5000)
                except Exception:
                    composer.press("Enter")
                time.sleep(3)
                shot(page, "3_sent")

                emailed = self._maybe_fill_email(page, reply_email)
                time.sleep(2)
                shot(page, "4_email")
                return SendResult(True, "pitch_sent" + ("+email" if emailed else ""))
            except Exception as e:
                return SendResult(False, f"{type(e).__name__}: {str(e)[:140]}")
            finally:
                try:
                    browser.close()
                except Exception:
                    pass

    @staticmethod
    def _maybe_fill_email(page, reply_email: str) -> bool:
        for sel in EMAIL_SELECTORS:
            try:
                loc = page.locator(sel).first
                if loc.count() and loc.is_visible(timeout=1500):
                    loc.fill(reply_email)
                    time.sleep(0.4)
                    try:
                        loc.press("Enter")
                    except Exception:
                        pass
                    for sub in SUBMIT_SELECTORS:
                        try:
                            bl = page.locator(sub).first
                            if bl.count() and bl.is_visible(timeout=800):
                                bl.click(timeout=1500)
                                break
                        except Exception:
                            continue
                    return True
            except Exception:
                continue
        return False
