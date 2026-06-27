"""WidgetDriver: the shared engine for the DOM-drive family of Chat Widgets.

Most chat vendors (Tidio, Crisp, Tawk, Shopify Inbox, ...) are driven the same way: launch a
stealthed browser, load the site, wait for the widget to come up, open it, reach the composer
(sometimes past a Home screen), type the Pitch, get past the email gate, and confirm delivery.
What differs between vendors is *data*, not control flow: which scope selector the widget lives
under, the JS predicate that says it is ready, the labels that open a conversation, how the email
gate works, and how a send is confirmed. WidgetDriver owns the flow; a VendorConfig supplies the
data. Adding such a vendor is a new VendorConfig, not a new class (ADR-0007).

This is the verbatim Tidio send() flow (research/tidio-injection.md, ADR-0003 wire-confirmed
delivery) lifted behind the config seam, so a Tidio run through WidgetDriver(TIDIO) behaves
byte-for-byte as the old hand-written TidioAdapter did. Vendors whose SEND is a JS API rather
than a DOM drive (e.g. Gorgias) do NOT belong here; they stay hand-written classes.

Env: HEADED=1 (visible window), TIDIO_DEBUG=1 (screenshot to /tmp/tidio_dbg_sent.png).
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass

from .injector import SendResult
from .proxy import playwright_proxy


@dataclass(frozen=True)
class VendorConfig:
    """The per-vendor data the shared WidgetDriver needs to drive one Chat Widget.

    email_strategy: how the email gate works -
        "prechat_then_api" - a pre-chat email field may appear; fill+send it, else attach the
                             email through email_api_js (Tidio).
        "none"            - no email gate.
    confirm_strategy: how a send is confirmed -
        "wire_token" - watch the websocket for a frame carrying our Pitch token (honest, no
                       false positives; ADR-0003). Needs confirm_frame_marker.
        "none"       - assume sent once the composer submitted.
    """
    vendor: str
    widget_scope: str | None            # shadow host / scope selector; None = whole page
    ready_predicate: str                # JS expr, truthy once the widget is ready
    ready_fallback_predicate: str       # JS expr returned if readiness times out
    ready_timeout_ms: int
    not_ready_detail: str               # SendResult.detail when the widget never comes up
    open_js: str                        # JS statement that opens the widget
    entry_labels: tuple[str, ...]       # labels that open a conversation from a Home screen
    email_strategy: str
    email_api_js: str | None            # JS statement (references `e`) to attach the email
    confirm_strategy: str
    confirm_frame_marker: str | None    # websocket frame marker for "wire_token"


class WidgetDriver:
    def __init__(self, config: VendorConfig):
        self.config = config

    # ----- pure helpers (browserless, unit-tested) ---------------------------------------

    @staticmethod
    def _target_url(domain: str) -> str:
        """The URL to load for a Brand. A bare domain gets https; an explicit scheme is kept
        as-is, so the driver can be pointed at an http test page or an http-only store."""
        d = (domain or "").strip()
        if d.startswith("http://") or d.startswith("https://"):
            return d
        return "https://" + d

    @staticmethod
    def _scoped(scope: str | None, inner: str) -> str:
        """Prefix every comma-separated selector in `inner` with the widget `scope` so a query
        stays inside the widget and off the page's own forms. A None scope means page-level."""
        if not scope:
            return inner
        return ", ".join(f"{scope} {part.strip()}" for part in inner.split(","))

    @staticmethod
    def _pitch_token(pitch: str) -> str | None:
        """A distinctive ASCII run from the Pitch to look for on the wire. Prefer a 6+ char run;
        fall back to the longest alnum run of any length so it is always JSON-safe."""
        words = re.findall(r"[A-Za-z0-9]{6,}", pitch) or re.findall(r"[A-Za-z0-9]+", pitch)
        return max(words, key=len) if words else None

    @staticmethod
    def _pick_entry_label(entry_labels, button_texts):
        """Given the widget's visible clickable texts, return the on-screen text to click to start
        a conversation, or None. The vendor's entry_labels are tried first as case-insensitive
        substrings (so a wrapped 'Live Chat with us now' still works) and return the REAL on-screen
        text. As a last resort the bare 'Chat' bottom-nav tab is matched EXACTLY, so we never grab
        a 'chat' buried in another phrase and a real entry always beats the nav tab."""
        texts = [t for t in (button_texts or []) if t and t.strip()]
        for label in entry_labels:
            ll = label.lower()
            for t in texts:
                if ll in t.lower():
                    return t
        for t in texts:
            if t.strip().lower() == "chat":
                return t
        return None

    @staticmethod
    def _delivered(frames, token, marker):
        """True iff a send-marker frame carries our Pitch token (raw or JSON-escaped). With no
        usable token (Pitch is all punctuation/non-ASCII, ~never), fall back to the presence of
        a marker frame, which is the real send event."""
        if not marker:
            return False
        esc = json.dumps(token)[1:-1] if token else ""
        for f in frames:
            if isinstance(f, str) and marker in f:
                if not token or token in f or (esc and esc in f):
                    return True
        return False

    # ----- the live send (integration; proven by real runs) ------------------------------

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        from playwright.sync_api import sync_playwright

        cfg = self.config
        scope = cfg.widget_scope
        headed = os.environ.get("HEADED", "").lower() in ("1", "true", "yes")
        debug = bool(os.environ.get("TIDIO_DEBUG"))
        url = self._target_url(domain)
        frames: list = []
        token = self._pitch_token(pitch)

        ready_js = (
            "async () => {\n"
            "  const t0 = Date.now();\n"
            "  while (Date.now() - t0 < " + str(cfg.ready_timeout_ms) + ") {\n"
            "    if (" + cfg.ready_predicate + ") return true;\n"
            "    await new Promise(r => setTimeout(r, 300));\n"
            "  }\n"
            "  return !!(" + cfg.ready_fallback_predicate + ");\n"
            "}"
        )

        with sync_playwright() as p:
            browser = None
            try:
                channel = os.environ.get("BROWSER_CHANNEL", "chrome") or None
                browser = p.chromium.launch(
                    headless=not headed, channel=channel,
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
                if not page.evaluate(ready_js):
                    return SendResult(False, cfg.not_ready_detail)

                page.evaluate("() => { try { " + cfg.open_js + "; } catch(_){} }")
                time.sleep(2.5)
                self._dismiss_site_overlays(page)

                composer = self._composer(page)
                if composer is None:
                    self._click_entry(page)          # Home screen: composer is behind an entry
                    time.sleep(2)
                    composer = self._composer(page)
                if composer is None:
                    return SendResult(False, "no_composer")

                # Type the Pitch, sending newlines as Shift+Enter (soft line breaks) so an
                # embedded \n does not submit early and spill the rest into the next field.
                composer.click()
                for i, line in enumerate(pitch.split("\n")):
                    if i:
                        page.keyboard.press("Shift+Enter")
                    page.keyboard.type(line, delay=6)
                time.sleep(0.4)
                composer.press("Enter")
                time.sleep(2)

                prechat_blocked = self._handle_email_gate(page, frames, token, reply_email)

                if debug:
                    try:
                        page.screenshot(path="/tmp/tidio_dbg_sent.png")
                    except Exception:
                        pass

                if cfg.confirm_strategy == "none":
                    return SendResult(True, "pitch_sent")

                # Final confirmation: poll with a driver-pumping wait so a late framesent
                # callback flushes (a bare time.sleep does NOT pump the sync driver).
                deadline = time.time() + 6
                while time.time() < deadline:
                    if self._delivered(frames, token, cfg.confirm_frame_marker):
                        return SendResult(True, "delivered")
                    page.wait_for_timeout(250)
                if prechat_blocked:
                    return SendResult(False, "prechat_blocked_required_fields")
                return SendResult(False, "no_delivery_confirmation")
            except Exception as e:
                # Deliver-then-raise: if the Pitch already hit the wire, report it honestly so the
                # Ledger advances and we never re-pitch (double-send) the same store next run.
                if self._delivered(frames, token, cfg.confirm_frame_marker):
                    return SendResult(True, "delivered_then_error")
                return SendResult(False, f"{type(e).__name__}: {str(e)[:160]}")
            finally:
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass

    def _handle_email_gate(self, page, frames, token, reply_email) -> bool:
        """Get past the email gate. Returns True if a required pre-chat field still blocks Send.

        "prechat_then_api": if a pre-chat email field is visible, fill it (and any required name)
        and click Send, nudging a resend if the wire frame has not flushed; otherwise attach the
        email through the vendor API so the operator can still reply.
        """
        cfg = self.config
        if cfg.email_strategy == "none":
            return False

        scope = cfg.widget_scope
        email = page.locator(
            self._scoped(scope, "input[type='email'], input[placeholder*='email' i]")
        ).first
        if email.count() and email.is_visible(timeout=2000):
            self._fill_name(page)
            email.fill(reply_email, timeout=8000, force=True)
            send_btn = self._send_button(page)
            if send_btn is not None:
                try:
                    send_btn.click(timeout=4000, force=True)
                except Exception:
                    pass
            time.sleep(3)
            if not self._delivered(frames, token, cfg.confirm_frame_marker):
                # Resend nudge: read text generically (a contenteditable has no input_value())
                # and NEVER let a recovery error abort the send.
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
            # If a required field (phone/consent) still blocks Send, flag it distinctly so the
            # batch runner routes this store out of the retry loop.
            if not self._delivered(frames, token, cfg.confirm_frame_marker):
                try:
                    sb = self._send_button(page)
                    if sb is not None and sb.is_disabled(timeout=500):
                        return True
                except Exception:
                    pass
            return False

        # No pre-chat form: the Enter already sent. Attach the email via the vendor API so the
        # operator can reply. Guard the evaluate: the context may detach post-send.
        if cfg.email_api_js:
            try:
                page.evaluate(
                    "(e) => { try { " + cfg.email_api_js + "; } catch(_){} }", reply_email)
            except Exception:
                pass
        return False

    # ----- scoped DOM helpers ------------------------------------------------------------

    def _composer(self, page):
        loc = page.locator(
            self._scoped(self.config.widget_scope, "textarea, [contenteditable='true']")).first
        try:
            if loc.count() and loc.is_visible(timeout=1500):
                return loc
        except Exception:
            pass
        return None

    def _click_entry(self, page):
        """Reach the composer from a Home/menu screen by clicking an entry. Reads the widget's
        visible clickable texts, resolves which to click via _pick_entry_label, then clicks that
        exact element by index. A miss returns False (-> no_composer), never raises."""
        loc = page.locator(self._scoped(self.config.widget_scope, "button, [role='button']"))
        try:
            texts = loc.all_inner_texts()
        except Exception:
            return False
        picked = self._pick_entry_label(self.config.entry_labels, texts)
        if picked is None:
            return False
        try:
            target = loc.nth(texts.index(picked))
            if target.is_visible(timeout=2000):
                target.click(timeout=2000)
                return True
        except Exception:
            pass
        return False

    def _fill_name(self, page):
        """Fill a pre-chat name field if the survey requires one (no-op on email-only forms)."""
        name = page.locator(
            self._scoped(self.config.widget_scope,
                         "input[name*='name' i], input[placeholder*='name' i]")).first
        try:
            if name.count() and name.is_visible(timeout=500):
                name.fill("Nikhil", timeout=4000, force=True)
        except Exception:
            pass

    def _send_button(self, page):
        """The widget Send control. Ordered: the proven visible-text 'Send' first, then icon/aria
        variants. First visible match wins; never matches outside the widget scope."""
        scope = self.config.widget_scope
        prefix = (scope + " ") if scope else ""
        candidates = (
            page.locator(f"{prefix}button", has_text=re.compile("send", re.I)),
            page.locator(f"{prefix}button[aria-label*='send' i]"),
            page.locator(f"{prefix}[role='button'][aria-label*='send' i]"),
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
        Scoped OUTSIDE the widget so we never close the chat itself."""
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
