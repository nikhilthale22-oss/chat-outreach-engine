"""TidioAdapter: the real Adapter for Tidio live-chat widgets.

Reverse-engineered live (research/tidio-injection.md). The findings that shape this:

- Tidio's widget renders in OPEN SHADOW DOM under a single host, div#tidio-chat. Playwright
  pierces open shadow roots, so we scope every interaction to "#tidio-chat" - that keeps us on
  the widget and off the page's own forms (e.g. a Klaviyo newsletter with its own email field;
  unscoped, input[placeholder*=email] matches 3 fields, scoped it matches the 1 right one).
- messageFromVisitor()/messageFromOperator() are UI-simulation only; they do NOT transmit. The
  real path is to drive the widget like a visitor: open -> (Home) click an entry like
  "Chat with us" -> type into the composer -> if a pre-chat form appears, fill the widget's
  email field and Send. The held message then flushes.
- A real send emits a "visitorNewMessage" websocket frame (with a server messageId). We capture
  framesent and only report sent=True when we SEE that frame carry our text - so SendResult is
  honest (no false positives). No CAPTCHA anywhere.

Hardened after an adversarial review for volume use (no false-negatives -> no double-send):
the final delivery check polls with a driver-pumping wait so a late frame flushes; an exception
after the wire-confirmed send still reports delivered; the resend nudge can never abort the send;
the delivery token is always JSON-safe; launch failures return a retryable result, not a raise.

Coverage caveat: only stores that embed Tidio via a direct code.tidio.co script tag initialise
under automation; Shopify app-embed injections do not (-> no_tidio_api, retryable).

Env: HEADED=1 (visible window), TIDIO_DEBUG=1 (screenshot to /tmp/tidio_dbg_sent.png).
"""
from __future__ import annotations

import json
import os
import re
import time

from ..injector import SendResult
from ..proxy import playwright_proxy

WIDGET = "#tidio-chat"  # Tidio's open-shadow-DOM host; scopes us to the widget
ENTRY_LABELS = ("Chat with us", "Send us a message", "New conversation",
                "Start a conversation", "Start chat", "Get in touch")


class TidioAdapter:
    vendor = "tidio"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        from playwright.sync_api import sync_playwright

        headed = os.environ.get("HEADED", "").lower() in ("1", "true", "yes")
        debug = bool(os.environ.get("TIDIO_DEBUG"))
        url = "https://" + domain
        frames: list = []
        # Distinctive token we look for on the wire. Prefer a 6+ char run; fall back to the
        # longest alnum run of any length so it is always pure ASCII (JSON-safe on the wire).
        words = re.findall(r"[A-Za-z0-9]{6,}", pitch) or re.findall(r"[A-Za-z0-9]+", pitch)
        token = max(words, key=len) if words else None

        with sync_playwright() as p:
            browser = None
            try:
                browser = p.chromium.launch(
                    headless=not headed, channel="chrome",
                    args=["--disable-blink-features=AutomationControlled"],
                )
                page = browser.new_context(
                    viewport={"width": 1366, "height": 900}, locale="en-US",
                    proxy=playwright_proxy(),
                    user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
                ).new_page()
                page.on("websocket",
                        lambda ws: ws.on("framesent", lambda pl: frames.append(pl)))

                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                ready = page.evaluate(
                    """async () => {
                        const t0 = Date.now();
                        while (Date.now() - t0 < 25000) {
                            const a = window.tidioChatApi;
                            if (a && a.readyEventWasFired) return true;
                            await new Promise(r => setTimeout(r, 300));
                        }
                        return !!window.tidioChatApi;
                    }"""
                )
                if not ready:
                    return SendResult(False, "no_tidio_api")

                page.evaluate("() => { try { window.tidioChatApi.open(); } catch(_){} }")
                time.sleep(2.5)
                self._dismiss_site_overlays(page)

                composer = self._composer(page)
                if composer is None:
                    self._click_entry(page)          # Home screen: composer is behind an entry
                    time.sleep(2)
                    composer = self._composer(page)
                if composer is None:
                    return SendResult(False, "no_composer")

                # Type the pitch, sending newlines as Shift+Enter (soft line breaks) so an
                # embedded \n does not submit early and spill the rest into the next field.
                composer.click()
                for i, line in enumerate(pitch.split("\n")):
                    if i:
                        page.keyboard.press("Shift+Enter")
                    page.keyboard.type(line, delay=6)
                time.sleep(0.4)
                composer.press("Enter")
                time.sleep(2)

                prechat_blocked = False
                email = page.locator(
                    f"{WIDGET} input[type='email'], {WIDGET} input[placeholder*='email' i]"
                ).first
                if email.count() and email.is_visible(timeout=2000):
                    # Some pre-chat surveys also require a name; fill it if present (no-op else).
                    self._fill_name(page)
                    email.fill(reply_email, timeout=8000, force=True)
                    send_btn = self._send_button(page)
                    if send_btn is not None:
                        try:
                            send_btn.click(timeout=4000, force=True)
                        except Exception:
                            pass
                    time.sleep(3)
                    if not self._delivered(frames, token):
                        # Resend nudge: read text generically (a contenteditable has no
                        # input_value()) and NEVER let a recovery error abort the send.
                        try:
                            c2 = self._composer(page)
                            if c2 is not None:
                                txt = c2.evaluate(
                                    "el => (el.value != null ? el.value : (el.textContent || ''))")
                                if (txt or "").strip():
                                    c2.press("Enter")
                                    time.sleep(2)
                        except Exception:
                            pass
                    # If a required field (phone/consent) still blocks Send, flag it distinctly
                    # so the batch runner routes this store out of the retry loop.
                    if not self._delivered(frames, token):
                        try:
                            sb = self._send_button(page)
                            if sb is not None and sb.is_disabled(timeout=500):
                                prechat_blocked = True
                        except Exception:
                            pass
                else:
                    # No pre-chat: the Enter already sent. Attach the email via the API so the
                    # operator can reply. Guard the evaluate: the context may detach post-send.
                    try:
                        page.evaluate(
                            "(e) => { try { window.tidioChatApi.setContactProperties({email: e}); }"
                            " catch(_){} }", reply_email,
                        )
                    except Exception:
                        pass

                if debug:
                    try:
                        page.screenshot(path="/tmp/tidio_dbg_sent.png")
                    except Exception:
                        pass

                # Final confirmation: poll with a driver-pumping wait so a late framesent
                # callback flushes (a bare time.sleep does NOT pump the sync driver).
                deadline = time.time() + 6
                while time.time() < deadline:
                    if self._delivered(frames, token):
                        return SendResult(True, "delivered")
                    page.wait_for_timeout(250)
                if prechat_blocked:
                    return SendResult(False, "prechat_blocked_required_fields")
                return SendResult(False, "no_delivery_confirmation")
            except Exception as e:
                # Deliver-then-raise: if the pitch already hit the wire, report it honestly so the
                # Ledger advances and we never re-pitch (double-send) the same store next run.
                if self._delivered(frames, token):
                    return SendResult(True, "delivered_then_error")
                return SendResult(False, f"{type(e).__name__}: {str(e)[:160]}")
            finally:
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass

    @staticmethod
    def _composer(page):
        loc = page.locator(f"{WIDGET} textarea, {WIDGET} [contenteditable='true']").first
        try:
            if loc.count() and loc.is_visible(timeout=1500):
                return loc
        except Exception:
            pass
        return None

    @staticmethod
    def _click_entry(page):
        for label in ENTRY_LABELS:
            try:
                btn = page.locator(WIDGET).get_by_text(label, exact=False).first
                if btn.count() and btn.is_visible(timeout=700):
                    btn.click(timeout=2000)
                    return True
            except Exception:
                continue
        return False

    @staticmethod
    def _fill_name(page):
        """Fill a pre-chat name field if the survey requires one (no-op on email-only forms)."""
        name = page.locator(
            f"{WIDGET} input[name*='name' i], {WIDGET} input[placeholder*='name' i]"
        ).first
        try:
            if name.count() and name.is_visible(timeout=500):
                name.fill("Nikhil", timeout=4000, force=True)
        except Exception:
            pass

    @staticmethod
    def _send_button(page):
        """The widget Send control. Ordered: the proven visible-text 'Send' first, then
        icon/aria-only variants. First visible match wins; never matches outside #tidio-chat."""
        candidates = (
            page.locator(f"{WIDGET} button", has_text=re.compile("send", re.I)),
            page.locator(f"{WIDGET} button[aria-label*='send' i]"),
            page.locator(f"{WIDGET} [role='button'][aria-label*='send' i]"),
        )
        for loc in candidates:
            try:
                first = loc.first
                if first.count() and first.is_visible(timeout=500):
                    return first
            except Exception:
                continue
        return None

    @staticmethod
    def _dismiss_site_overlays(page):
        """Close page-level modals (newsletter/consent) that can obscure the widget's fields.
        Scoped OUTSIDE the Tidio widget so we never close the chat itself."""
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        for sel in ['[class*="klaviyo" i] button[aria-label*="lose" i]',
                    'button[aria-label="Close dialog" i]', '[id*="onetrust-accept"]',
                    'button[aria-label*="lose" i]:not(#tidio-chat *)']:
            try:
                loc = page.locator(sel).first
                if loc.count() and loc.is_visible(timeout=300):
                    loc.click(timeout=800)
            except Exception:
                continue

    @staticmethod
    def _delivered(frames, token):
        """True iff a visitorNewMessage frame carries our pitch token (raw or JSON-escaped).
        With no usable token (pitch is all punctuation/non-ASCII, ~never), fall back to the
        presence of a visitorNewMessage frame, which is the real send event."""
        esc = json.dumps(token)[1:-1] if token else ""
        for f in frames:
            if isinstance(f, str) and "visitorNewMessage" in f:
                if not token or token in f or (esc and esc in f):
                    return True
        return False
