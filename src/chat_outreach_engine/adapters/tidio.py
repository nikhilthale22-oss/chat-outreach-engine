"""TidioAdapter: Adapter for the Tidio live-chat widget.

Tidio exposes window.tidioChatApi (open/close/etc.) but no reliable visitor-send API, so we
open via the API and drive the composer textarea inside the Tidio chat iframe. Verified: the
send flow has NO CAPTCHA (research/tidio-injection.md), unlike Shopify Inbox. A pre-chat
email form (if the merchant enabled one) is filled adaptively.

Env: HEADED=1 (visible window), TIDIO_DEBUG=1 (phase screenshots to /tmp/tidio_dbg_*.png).
"""
from __future__ import annotations

import os
import time

from ..injector import SendResult


class TidioAdapter:
    vendor = "tidio"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        from playwright.sync_api import sync_playwright

        headed = os.environ.get("HEADED", "").lower() in ("1", "true", "yes")
        debug = bool(os.environ.get("TIDIO_DEBUG"))
        url = "https://" + domain

        def shot(page, n):
            if debug:
                try:
                    page.screenshot(path=f"/tmp/tidio_dbg_{n}.png")
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
                try:
                    page.wait_for_function(
                        "() => typeof window.tidioChatApi === 'object' && window.tidioChatApi",
                        timeout=20000,
                    )
                except Exception:
                    return SendResult(False, "no_tidio_api")

                self._dismiss_popups(page)
                composer = self._open_and_find_composer(page, shot)
                if composer is None:
                    return SendResult(False, "no_composer")

                self._maybe_email(page, reply_email)
                composer.fill(pitch)
                time.sleep(0.5)
                shot(page, "2_typed")

                self._maybe_email(page, reply_email)
                composer.press("Enter")
                time.sleep(3)
                shot(page, "3_sent")
                return SendResult(True, "pitch_sent")
            except Exception as e:
                return SendResult(False, f"{type(e).__name__}: {str(e)[:140]}")
            finally:
                try:
                    browser.close()
                except Exception:
                    pass

    @staticmethod
    def _dismiss_popups(page):
        """Close common marketing modals that sit over the page and block the widget."""
        for _ in range(2):
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            for sel in ['button[aria-label*="lose" i]', 'button[title*="lose" i]',
                        'button.close', '[class*="close" i] button', '[data-testid*="close" i]',
                        '[aria-label="Close dialog" i]']:
                try:
                    loc = page.locator(sel).first
                    if loc.count() and loc.is_visible(timeout=300):
                        loc.click(timeout=800)
                except Exception:
                    continue
            time.sleep(0.4)

    def _open_and_find_composer(self, page, shot):
        try:
            page.evaluate("() => { try { window.tidioChatApi.open(); } catch(e){} }")
        except Exception:
            pass
        time.sleep(3)
        shot(page, "1_open")
        c = self._find_composer(page, timeout=6)
        if c is not None:
            return c
        # fallback: click the Tidio launcher bubble/iframe directly
        for sel in ["#tidio-chat-iframe", '[id*="tidio"]']:
            try:
                loc = page.locator(sel).first
                if loc.count() and loc.is_visible(timeout=800):
                    loc.click(timeout=2000)
                    break
            except Exception:
                continue
        time.sleep(3)
        shot(page, "1b_launcher")
        return self._find_composer(page, timeout=8)

    @staticmethod
    def _find_composer(page, timeout=12):
        deadline = time.time() + timeout
        while time.time() < deadline:
            for f in page.frames:
                try:
                    loc = f.locator("textarea")
                    if loc.count() and loc.first.is_visible(timeout=400):
                        return loc.first
                except Exception:
                    continue
            time.sleep(1)
        return None

    @staticmethod
    def _maybe_email(page, reply_email):
        for f in page.frames:
            for sel in ['input[type="email"]', 'input[name*="email"]', 'input[placeholder*="mail"]']:
                try:
                    loc = f.locator(sel).first
                    if loc.count() and loc.is_visible(timeout=400):
                        loc.fill(reply_email)
                        return True
                except Exception:
                    continue
        return False
