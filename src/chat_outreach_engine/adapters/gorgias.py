"""GorgiasAdapter: the real Adapter for Gorgias chat widgets.

Ports the proven send flow: open the site, wait for window.GorgiasChat, open it,
capture the reply email at the gate, and send the Pitch. Playwright is imported
lazily so the package imports without it in test environments.
"""
from __future__ import annotations

import json
import os
import time

from ..injector import SendResult
from ..proxy import playwright_proxy


class GorgiasAdapter:
    vendor = "gorgias"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        from playwright.sync_api import sync_playwright

        url = "https://" + domain
        with sync_playwright() as p:
            channel = os.environ.get("BROWSER_CHANNEL", "chrome") or None
            browser = p.chromium.launch(
                headless=True, channel=channel,
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = browser.new_context(
                viewport={"width": 1366, "height": 768}, locale="en-US",
                proxy=playwright_proxy(),
            ).new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                time.sleep(2)
                ready = page.evaluate(
                    """async () => {
                        const t0 = Date.now();
                        while (Date.now() - t0 < 15000) {
                            if (window.GorgiasChat) return true;
                            await new Promise(r => setTimeout(r, 300));
                        }
                        return false;
                    }"""
                )
                if not ready:
                    return SendResult(False, "no_gorgias")
                page.evaluate(
                    """async () => {
                        try { const r = window.GorgiasChat.init && window.GorgiasChat.init();
                              if (r && r.then) await r; } catch(_) {}
                        try { window.GorgiasChat.open && window.GorgiasChat.open(); } catch(_) {}
                    }"""
                )
                time.sleep(1.5)
                page.evaluate(
                    f"() => {{ try {{ window.GorgiasChat.captureUserEmail "
                    f"&& window.GorgiasChat.captureUserEmail({json.dumps(reply_email)}); }} catch(_) {{}} }}"
                )
                time.sleep(1.5)
                page.evaluate(f"() => window.GorgiasChat.sendMessage({json.dumps(pitch)})")
                time.sleep(3)
                return SendResult(True, "pitch_sent")
            except Exception as e:
                return SendResult(False, f"{type(e).__name__}: {str(e)[:160]}")
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
