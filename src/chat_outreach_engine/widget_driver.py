"""WidgetDriver: the shared engine for the DOM-drive family of Chat Widgets.

Most chat vendors (Tidio, Tawk, Crisp, Shopify Inbox, ...) are driven the same way: launch a
stealthed browser, load the site, wait for the widget to come up, open it, reach the composer
(sometimes past a Home screen), type the Pitch, get past the email gate, and confirm delivery.
What differs between vendors is *data*, not control flow: which scope selector the widget lives
under, the JS predicate that says it is ready, the labels that open a conversation, how the email
gate works, and how a send is confirmed. WidgetDriver owns the flow; a VendorConfig supplies the
data. Adding such a vendor is a new VendorConfig, not a new class (ADR-0007).

Some widgets render their UI in a same-origin iframe with no stable URL/name (Tawk's v4 widget
uses an `about:srcdoc` iframe). For those, the config sets `widget_frame_marker` - a selector that
only exists inside the widget frame - and the driver resolves that frame by content and scopes the
composer/entry/email/send to it. The widget's JS API (open, ready, the confirm hook) still lives on
the top page, so those run page-level. Vendors whose SEND is a JS API rather than a DOM drive (e.g.
Gorgias) do NOT belong here; they stay hand-written classes.

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
        "none"            - no email gate (Tawk's default widget has none).
    confirm_strategy: how a send is confirmed -
        "wire_token"   - watch the websocket for a frame carrying our Pitch token (Tidio; ADR-0003).
        "callback_flag"- install a JS callback (confirm_setup_js) that records sent visitor messages
                         to window.__cw_confirm, then check our token appears (Tawk's onChatMessageVisitor).
        "none"         - assume sent once the composer submitted.
    entry_strategy: how to reach the composer from a Home screen -
        "button_texts" - read the clickable button texts and resolve via _pick_entry_label (Tidio).
        "by_text"      - click the first visible element matching an entry label by text (Tawk).
    widget_frame_marker: a selector that exists only inside the widget's iframe. When set, the driver
        resolves that frame by content and scopes DOM ops to it; when None, ops run on the page.
    """
    vendor: str
    widget_scope: str | None            # shadow host / scope selector; None = page (or whole frame)
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
    # --- optional, default to the Tidio shape so existing configs are unaffected ---
    composer_selector: str = "textarea, [contenteditable='true']"
    entry_selector: str = "button, [role='button']"
    entry_strategy: str = "button_texts"
    widget_frame_marker: str | None = None
    confirm_setup_js: str | None = None  # JS run on the page before send, for "callback_flag"


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
                if cfg.confirm_setup_js:
                    try:
                        page.evaluate("() => { try { " + cfg.confirm_setup_js + " } catch(_){} }")
                    except Exception:
                        pass

                # The widget UI may live in a same-origin iframe with no stable URL (Tawk). Resolve
                # the surface (frame or page) we drive the composer/entry/email/send on.
                surface = self._surface(page)

                composer = self._composer(surface)
                if composer is None:
                    self._click_entry(surface)       # Home screen: composer is behind an entry
                    time.sleep(2)
                    surface = self._surface(page)     # the view may have re-rendered the frame
                    composer = self._composer(surface)
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

                prechat_blocked = self._handle_email_gate(surface, page, frames, token, reply_email)

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
                    if self._confirmed(page, frames, token):
                        return SendResult(True, "delivered")
                    page.wait_for_timeout(250)
                if prechat_blocked:
                    return SendResult(False, "prechat_blocked_required_fields")
                return SendResult(False, "no_delivery_confirmation")
            except Exception as e:
                # Deliver-then-raise: if the Pitch already hit the wire, report it honestly so the
                # Ledger advances and we never re-pitch (double-send) the same store next run.
                if self._confirmed(page, frames, token):
                    return SendResult(True, "delivered_then_error")
                return SendResult(False, f"{type(e).__name__}: {str(e)[:160]}")
            finally:
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass

    # ----- surface + confirm ------------------------------------------------------------

    def _surface(self, page):
        """The Page or Frame the composer lives on. When widget_frame_marker is set, find the frame
        that contains it (the widget's same-origin iframe, which has no stable URL/name) and return
        it; otherwise the page. Waits briefly because the frame appears after the widget opens."""
        marker = self.config.widget_frame_marker
        if not marker:
            return page
        for _ in range(24):  # heavy stores render the widget iframe slowly; wait up to ~12s
            try:
                for fr in page.frames:
                    try:
                        if fr.locator(marker).count() > 0:
                            return fr
                    except Exception:
                        continue
            except Exception:
                pass
            try:
                page.wait_for_timeout(500)
            except Exception:
                break
        return page  # frame never appeared -> composer lookup fails -> no_composer (retryable)

    def _confirmed(self, page, frames, token):
        """Was the Pitch really sent? wire_token: a marker websocket frame carries the token.
        callback_flag: the vendor's visitor-message callback recorded our token to window.__cw_confirm."""
        cs = self.config.confirm_strategy
        if cs == "wire_token":
            return self._delivered(frames, token, self.config.confirm_frame_marker)
        if cs == "callback_flag":
            try:
                blob = page.evaluate("() => (window.__cw_confirm || []).join('\\n')")
            except Exception:
                return False
            return bool(blob) if not token else (token in blob)
        return False

    def _handle_email_gate(self, surface, page, frames, token, reply_email) -> bool:
        """Get past the email gate. Returns True if a required pre-chat field still blocks Send.

        "none": no gate. "prechat_then_api": if a pre-chat email field is visible, fill it (and any
        required name) and click Send, nudging a resend if the wire frame has not flushed; otherwise
        attach the email through the vendor API so the operator can still reply.
        """
        cfg = self.config
        if cfg.email_strategy == "none":
            return False

        scope = cfg.widget_scope
        email = surface.locator(
            self._scoped(scope, "input[type='email'], input[placeholder*='email' i]")
        ).first
        if email.count() and email.is_visible(timeout=2000):
            self._fill_name(surface)
            email.fill(reply_email, timeout=8000, force=True)
            send_btn = self._send_button(surface)
            if send_btn is not None:
                try:
                    send_btn.click(timeout=4000, force=True)
                except Exception:
                    pass
            time.sleep(3)
            if not self._confirmed(page, frames, token):
                # Resend nudge: read text generically (a contenteditable has no input_value())
                # and NEVER let a recovery error abort the send.
                try:
                    c2 = self._composer(surface)
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
            if not self._confirmed(page, frames, token):
                try:
                    sb = self._send_button(surface)
                    if sb is not None and sb.is_disabled(timeout=500):
                        return True
                except Exception:
                    pass
            return False

        # No pre-chat form: the Enter already sent. Attach the email via the vendor API so the
        # operator can reply. Guard the evaluate: the context may detach post-send.
        if cfg.email_api_js:
            try:
                surface.evaluate(
                    "(e) => { try { " + cfg.email_api_js + "; } catch(_){} }", reply_email)
            except Exception:
                pass
        return False

    # ----- scoped DOM helpers (operate on the surface: page or widget frame) --------------

    def _composer(self, surface):
        """The first VISIBLE composer on the surface. (Tawk renders two matching textareas, one
        hidden behind the Home card; Tidio has one - in both cases we want the visible one.)"""
        loc = surface.locator(self._scoped(self.config.widget_scope, self.config.composer_selector))
        try:
            for i in range(min(loc.count(), 6)):
                el = loc.nth(i)
                if el.is_visible(timeout=1200):
                    return el
        except Exception:
            pass
        return None

    def _click_entry(self, surface):
        """Reach the composer from a Home/menu screen by clicking an entry. Never raises.
        "button_texts" (Tidio): read the clickable button texts, resolve via _pick_entry_label,
        click that exact element. "by_text" (Tawk): click the first visible element matching an
        entry label by its text (the 'New Conversation' card is not a <button>)."""
        cfg = self.config
        if cfg.entry_strategy == "by_text":
            for label in cfg.entry_labels:
                try:
                    loc = surface.get_by_text(label, exact=False).first
                    if loc.count() and loc.is_visible(timeout=1000):
                        loc.click(timeout=2500)
                        return True
                except Exception:
                    continue
            return False

        loc = surface.locator(self._scoped(cfg.widget_scope, cfg.entry_selector))
        try:
            texts = loc.all_inner_texts()
        except Exception:
            return False
        picked = self._pick_entry_label(cfg.entry_labels, texts)
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

    def _fill_name(self, surface):
        """Fill a pre-chat name field if the survey requires one (no-op on email-only forms)."""
        name = surface.locator(
            self._scoped(self.config.widget_scope,
                         "input[name*='name' i], input[placeholder*='name' i]")).first
        try:
            if name.count() and name.is_visible(timeout=500):
                name.fill("Nikhil", timeout=4000, force=True)
        except Exception:
            pass

    def _send_button(self, surface):
        """The widget Send control. Ordered: the proven visible-text 'Send' first, then icon/aria
        variants. First visible match wins; never matches outside the widget scope."""
        scope = self.config.widget_scope
        prefix = (scope + " ") if scope else ""
        candidates = (
            surface.locator(f"{prefix}button", has_text=re.compile("send", re.I)),
            surface.locator(f"{prefix}button[aria-label*='send' i]"),
            surface.locator(f"{prefix}[role='button'][aria-label*='send' i]"),
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
