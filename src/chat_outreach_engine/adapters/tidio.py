"""TidioAdapter: the real Adapter for Tidio live-chat widgets.

Uses Tidio's JS API (window.tidioChatApi), the clean path - same shape as Gorgias.
Reverse-engineering finding (research/tidio-injection.md): Tidio's chat PANEL does NOT
render under automation, so DOM-driving the composer is a dead end. But the API IS fully
available when the widget loads (readyEventWasFired flips true) and exposes everything we
need: messageFromVisitor() sends a message as the visitor, setContactProperties()/
setVisitorData() attach the reply email so the operator's reply routes back. No CAPTCHA.

Caveat: only stores that embed Tidio via a direct code.tidio.co script tag initialise the
API under automation. Stores that inject Tidio dynamically via a Shopify app embed do not
load it headless -> no_tidio_api (correctly left Queued, retryable). Playwright is imported
lazily so the package imports without it in test environments.

Env: HEADED=1 (visible window), TIDIO_DEBUG=1 (screenshot to /tmp/tidio_dbg_*.png).
"""
from __future__ import annotations

import json
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

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=not headed, channel="chrome",
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = browser.new_context(
                viewport={"width": 1366, "height": 900}, locale="en-US",
                user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
            ).new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)

                # Wait for the API to load AND fire its ready event (queued calls only run after).
                ready = page.evaluate(
                    """async () => {
                        const t0 = Date.now();
                        while (Date.now() - t0 < 25000) {
                            const a = window.tidioChatApi;
                            if (a && a.readyEventWasFired) return true;
                            await new Promise(r => setTimeout(r, 300));
                        }
                        return !!(window.tidioChatApi);
                    }"""
                )
                if not ready:
                    return SendResult(False, "no_tidio_api")

                # Attach the reply email so the operator's reply routes back (ADR-0002).
                page.evaluate(
                    f"""(email) => {{
                        const a = window.tidioChatApi;
                        try {{ a.setContactProperties && a.setContactProperties({{email}}); }} catch(_) {{}}
                        try {{ a.setVisitorData && a.setVisitorData(
                            {{distinct_id: email, email}}); }} catch(_) {{}}
                    }}""",
                    reply_email,
                )
                # open() inits the conversation session (no visible panel under automation).
                page.evaluate("() => { try { window.tidioChatApi.open(); } catch(_) {} }")
                time.sleep(1.5)

                # Send the Pitch as the visitor (the clean API equivalent of typing + Enter).
                page.evaluate(
                    f"() => window.tidioChatApi.messageFromVisitor({json.dumps(pitch)})"
                )
                time.sleep(3)
                if debug:
                    try:
                        page.screenshot(path="/tmp/tidio_dbg_sent.png")
                    except Exception:
                        pass
                return SendResult(True, "pitch_sent_via_api")
            except Exception as e:
                return SendResult(False, f"{type(e).__name__}: {str(e)[:160]}")
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
