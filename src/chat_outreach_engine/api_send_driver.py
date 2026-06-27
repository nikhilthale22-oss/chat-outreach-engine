"""ApiSendDriver: the shared engine for the API-SEND family of Chat Widgets.

Some vendors transmit a visitor message through a JavaScript call rather than by typing into a
composer (Gorgias, Intercom `startConversation`, Zendesk messaging `sendMessage`). For those there is
no DOM to drive: open the widget, fire the vendor's send JS with the Pitch, and confirm the message
rendered. This is the API-send counterpart to WidgetDriver/VendorConfig (ADR-0007's "API-send vendors
do not belong on the DOM-drive driver").

Confirm reuses the dom_echo idea generically: an api-send widget still RENDERS the sent message in its
UI, so we confirm when our Pitch token appears in any frame's text. That keeps SendResult honest without
a vendor-specific wire format.

STATUS: the send path here is NOT yet proven by a real send (that needs a live merchant pitch, done with
a human in the loop). Treat api-send adapters as wired-but-unverified until a real send confirms transmit.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

from .injector import SendResult
from .proxy import playwright_proxy
from .widget_driver import WidgetDriver

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


@dataclass(frozen=True)
class ApiVendorConfig:
    """Per-vendor data for an API-send widget.

    send_js: a JS statement that transmits the Pitch. It receives `m` (the Pitch text) and `e` (the
        reply email) as arguments, e.g. "window.Intercom('startConversation', m)".
    """
    vendor: str
    ready_predicate: str
    ready_fallback_predicate: str
    ready_timeout_ms: int
    not_ready_detail: str
    open_js: str | None
    send_js: str
    confirm_strategy: str = "dom_echo_any"   # token appears in any frame's text | "none"


class ApiSendDriver:
    def __init__(self, config: ApiVendorConfig):
        self.config = config

    def _confirmed(self, page, token):
        if self.config.confirm_strategy != "dom_echo_any" or not token:
            return False
        for fr in page.frames:
            try:
                txt = fr.evaluate("() => (document.body && document.body.innerText) || ''")
                if token in txt:
                    return True
            except Exception:
                continue
        return False

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        from playwright.sync_api import sync_playwright

        cfg = self.config
        headed = os.environ.get("HEADED", "").lower() in ("1", "true", "yes")
        url = WidgetDriver._target_url(domain)
        token = WidgetDriver._pitch_token(pitch)
        ready_js = ("async () => { const t0=Date.now(); while (Date.now()-t0 < " + str(cfg.ready_timeout_ms) +
                    ") { if (" + cfg.ready_predicate + ") return true; await new Promise(r=>setTimeout(r,300)); }"
                    " return !!(" + cfg.ready_fallback_predicate + "); }")
        with sync_playwright() as p:
            browser = None
            page = None
            try:
                channel = os.environ.get("BROWSER_CHANNEL", "chrome") or None
                browser = p.chromium.launch(headless=not headed, channel=channel,
                                            args=["--disable-blink-features=AutomationControlled"])
                page = browser.new_context(viewport={"width": 1366, "height": 900}, locale="en-US",
                                           proxy=playwright_proxy(), user_agent=_UA).new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                if not page.evaluate(ready_js):
                    return SendResult(False, cfg.not_ready_detail)
                if cfg.open_js:
                    page.evaluate("() => { try { " + cfg.open_js + "; } catch(_){} }")
                    time.sleep(2.5)
                page.evaluate("([m, e]) => { try { " + cfg.send_js + "; } catch(_){} }", [pitch, reply_email])
                deadline = time.time() + 8
                while time.time() < deadline:
                    if self._confirmed(page, token):
                        return SendResult(True, "delivered")
                    page.wait_for_timeout(300)
                return SendResult(False, "no_delivery_confirmation")
            except Exception as e:
                if page is not None and self._confirmed(page, token):
                    return SendResult(True, "delivered_then_error")
                return SendResult(False, f"{type(e).__name__}: {str(e)[:160]}")
            finally:
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass
