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
    widget_frame_marker: str | None = None   # resolve the widget iframe by in-frame content (Tawk's about:srcdoc)
    widget_frame_url: str | None = None       # OR resolve it by a substring of the iframe URL (livechatinc.com, chatra.io)
    confirm_setup_js: str | None = None  # JS run on the page before send, for "callback_flag"
    # --- server-ACK confirm (ADR-0009): mark delivered only on the vendor's own "got it" receipt ---
    ack_response_re: str | None = None   # HTTP receipt: a POST 2xx whose URL matches this = server stored it
    ack_frame_re: str | None = None      # websocket receipt: a server->client frame matching this = server stored it
    # Some controlled-input forms (Help Scout's Beacon v2) ignore .fill()'s synthetic input event and
    # validate as empty -> never submit. Real per-key typing commits to their internal state (ADR-0010).
    fill_by_keystroke: bool = False
    # Some widgets gate the composer behind a pre-chat form that appears AFTER the entry click (Tawk
    # 'custom widget': required Name/Email/Phone + a Start button). When set, the driver fills+submits
    # that form during composer resolution so the composer renders; no-op when no such form is present.
    prechat_form_gate: bool = False


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

    def send(self, domain: str, pitch: str, reply_email: str, dry_run: bool = False) -> SendResult:
        """Pitch one Brand. dry_run reaches the composer and returns "composer_reached" WITHOUT
        typing or sending - the verify-to-composer path, safe to run unattended (nothing transmits)."""
        from playwright.sync_api import sync_playwright

        cfg = self.config
        headed = os.environ.get("HEADED", "").lower() in ("1", "true", "yes")
        debug = bool(os.environ.get("TIDIO_DEBUG"))
        url = self._target_url(domain)
        frames: list = []
        ack_http: list = []           # server-ACK: HTTP receipts matching cfg.ack_response_re (POST 2xx)
        ack_ws: list = []             # server-ACK: server->client ws frames matching cfg.ack_frame_re
        net_responses: list = []      # CW_NETLOG spike: server HTTP responses (form-POST acks)
        recv_frames: list = []        # CW_NETLOG spike: server->client websocket frames (chat acks)
        netlog = os.environ.get("CW_NETLOG")
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
            page = None
            surface = None
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
                # Capture what WE send (framesent) and, when the vendor has a known server receipt,
                # the vendor's own "got it" signal: a matching server->client ws frame (ack_frame_re)
                # or a POST 2xx whose URL matches ack_response_re. These are the ADR-0009 delivery ACKs.
                _ackfre = re.compile(cfg.ack_frame_re) if cfg.ack_frame_re else None
                _ackrre = re.compile(cfg.ack_response_re) if cfg.ack_response_re else None

                def _on_ws(ws):
                    ws.on("framesent", lambda pl: frames.append(pl))
                    if _ackfre is not None:
                        ws.on("framereceived",
                               lambda pl: ack_ws.append(pl)
                               if isinstance(pl, str) and _ackfre.search(pl) else None)
                page.on("websocket", _on_ws)

                if _ackrre is not None:
                    def _on_resp(r):
                        try:
                            if (r.request.method in ("POST", "PUT")
                                    and 200 <= r.status < 300 and _ackrre.search(r.url)):
                                ack_http.append((r.status, r.url))
                        except Exception:
                            pass
                    page.on("response", _on_resp)

                if netlog:
                    self._attach_netcapture(page, net_responses, recv_frames)

                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                if not page.evaluate(ready_js):
                    return SendResult(False, cfg.not_ready_detail)

                # Clear any load-time modal (newsletter/consent) BEFORE opening the widget - Escape is
                # safe here. After the widget is open we must NOT press Escape (Help Scout's Beacon
                # binds it to CLOSE the panel, which silently killed the Ask form -> no_composer on a
                # whole class of newer-Beacon stores), so the post-open pass is targeted buttons only.
                self._dismiss_site_overlays(page, use_escape=True, widget_scope=cfg.widget_scope)
                page.evaluate("() => { try { " + cfg.open_js + "; } catch(_){} }")
                time.sleep(2.5)
                self._dismiss_site_overlays(page, use_escape=False, widget_scope=cfg.widget_scope)
                if cfg.confirm_setup_js:
                    try:
                        page.evaluate("() => { try { " + cfg.confirm_setup_js + " } catch(_){} }")
                    except Exception:
                        pass

                # The widget UI may live in a same-origin iframe with no stable URL (Tawk). Resolve
                # the surface (frame or page) we drive the composer/entry/email/send on.
                surface = self._surface(page)

                composer = self._composer(surface)
                # Grace wait: many widgets open STRAIGHT to the composer (Zendesk messaging, Crisp,
                # Chatra, LiveChat) - it just renders a few seconds after open. Give it time to appear
                # BEFORE assuming a Home screen and clicking an entry, because a premature/wrong entry
                # click is slow and can reset a widget that had no entry - the intermittent Zendesk
                # no_composer race (composer provably present, but missed while we flailed on entries).
                for _ in range(6):
                    if composer is not None:
                        break
                    page.wait_for_timeout(1000)
                    surface = self._surface(page)
                    composer = self._composer(surface)
                if composer is None:
                    self._click_entry(surface)       # genuine Home screen: composer is behind an entry
                    time.sleep(2)
                    surface = self._surface(page)     # the view may have re-rendered the frame
                    composer = self._composer(surface)
                # Slow widgets (Help Scout's Beacon navigates to /ask/message/ asynchronously) may
                # not have rendered the composer yet; wait + retry a few times. Fast widgets already
                # have it and skip the loop instantly. A pre-chat form gate (Tawk custom widgets) is
                # filled+submitted here so the composer it hides can render.
                for _ in range(4):
                    if composer is not None:
                        break
                    # Filling+submitting the pre-chat form opens a live chat (a real footprint), so it
                    # NEVER runs under dry_run - dry_run must transmit/leave nothing.
                    if cfg.prechat_form_gate and not dry_run:
                        self._fill_prechat_and_start(surface, reply_email)
                    page.wait_for_timeout(1500)
                    surface = self._surface(page)
                    composer = self._composer(surface)
                if composer is None:
                    # Offline leave-a-message form: a contact_form vendor whose live composer never
                    # appeared may be showing a ticket form (Tawk offline: Name/Email/Message + Submit).
                    # If a form with a MESSAGE field is present, fill + submit it. (LiveChat/Help Scout
                    # reach their offline form via the normal composer path, so they never land here.)
                    if cfg.email_strategy == "contact_form":
                        msg_field = self._offline_form_message_field(surface)
                        if msg_field is not None and self._is_contact_form(surface):
                            if dry_run:
                                return SendResult(True, "offline_form_reached")
                            return self._submit_contact_form(surface, page, msg_field, pitch,
                                                             reply_email, debug, ack_http)
                    return SendResult(False, "no_composer")
                if os.environ.get("CW_DUMP"):
                    print(self._dump_form(surface), flush=True)
                    return SendResult(False, "dump_done")
                if dry_run:
                    # "composer_reached" must certify we could actually DRIVE this box, not merely
                    # that an element is visible. Focus it (non-transmitting) and confirm focus took;
                    # this is exactly the capability the real send needs now that send focuses rather
                    # than requiring an actionable click. A visible-but-undriveable node reports
                    # composer_unfocusable instead of a green false positive.
                    try:
                        composer.evaluate("el => el.focus()")
                        focused = composer.evaluate(
                            "el => document.activeElement === el "
                            "|| (el.contains && el.contains(document.activeElement))")
                    except Exception:
                        focused = False
                    return SendResult(True, "composer_reached" if focused else "composer_unfocusable")

                # Contact-form vendors (LiveChat offline "leave a message", Help Scout "Ask"): the
                # surface is a multi-field FORM to fill + submit, not a chat thread. Only take this
                # path when a real form is actually present, so an ONLINE live composer falls through
                # to the normal chat send below.
                if cfg.email_strategy == "contact_form" and self._is_contact_form(surface):
                    return self._submit_contact_form(surface, page, composer, pitch,
                                                     reply_email, debug, ack_http)

                # Focus the composer. A plain click suffices for most widgets, but some composers
                # never satisfy Playwright's actionability STABILITY check: HubSpot's is an auto-
                # expanding contenteditable (VizExExpandingInput) that reflows every animation frame,
                # so .click() waits out its whole timeout on a perfectly usable box. Bound the click
                # and fall back to a direct focus(), which needs no actionability wait. Remember which
                # path we took - a stability-refused composer refuses composer.press("Enter") too.
                clicked_ok = True
                try:
                    composer.click(timeout=5000)
                except Exception:
                    clicked_ok = False
                    try:
                        composer.evaluate("el => el.focus()")
                    except Exception:
                        pass
                # Type the Pitch, sending newlines as Shift+Enter (soft line breaks) so an
                # embedded \n does not submit early and spill the rest into the next field.
                for i, line in enumerate(pitch.split("\n")):
                    if i:
                        page.keyboard.press("Shift+Enter")
                    page.keyboard.type(line, delay=15)
                time.sleep(0.4)
                # Self-heal: keyboard.type drops characters on fast React composers (Tawk dropped
                # ~half a 132-char pitch at 6ms), which truncates the send. Verify the composer holds
                # the whole pitch; if it came up short, set it directly with fill() (atomic + fires the
                # input event) so the FULL pitch is always what gets sent.
                try:
                    _typed = composer.evaluate(
                        "el => (el.value != null ? el.value : (el.textContent || ''))")
                    if len((_typed or "").strip()) < len(pitch.strip()) - 2:
                        composer.fill(pitch)
                except Exception:
                    pass
                if os.environ.get("CW_DIAG"):
                    try:
                        _v = composer.evaluate(
                            "el => (el.value != null ? el.value : (el.textContent || ''))")
                        print(f"[CW_DIAG] composer_len={len(_v)} value={_v!r}", flush=True)
                    except Exception as _e:
                        print(f"[CW_DIAG] read failed: {_e!r}", flush=True)
                    if os.environ.get("CW_DIAG_NOSEND"):
                        return SendResult(False, "diag_nosend")
                # Send. A click-focused composer takes composer.press; a focus()-fallback composer
                # (HubSpot) would stall on Locator.press's own actionability wait, so send Enter at
                # the keyboard level to the already-focused composer.
                if clicked_ok:
                    composer.press("Enter")
                else:
                    page.keyboard.press("Enter")
                time.sleep(2)

                # Chatra holds the message until a name/email intro is typed into the SAME composer.
                # ack_ws carries any server "Messages added" echo captured meanwhile (the receipt).
                if cfg.email_strategy == "composer_intro":
                    return self._finish_composer_intro(surface, page, pitch, reply_email, debug, ack_ws)

                prechat_blocked = self._handle_email_gate(surface, page, frames, token, reply_email)

                if os.environ.get("CW_DUMP2"):
                    try:
                        surface = self._surface(page)
                    except Exception:
                        pass
                    print(self._dump_form(surface), flush=True)
                    return SendResult(False, "dump2_done")

                if debug:
                    try:
                        page.screenshot(path="/tmp/tidio_dbg_sent.png")
                    except Exception:
                        pass

                if cfg.confirm_strategy == "none":
                    return SendResult(True, "pitch_sent")

                # Final confirmation: poll with a driver-pumping wait so a late frame flushes (a bare
                # time.sleep does NOT pump the sync driver). For a vendor with a known server receipt
                # (ack_frame_re) this now requires the SERVER's ack, not just our own sent frame.
                deadline = time.time() + 6
                while time.time() < deadline:
                    # A server HTTP receipt (a POST 2xx matching this vendor's ack_response_re) is the
                    # strongest proof and is independent of the widget UI. Report it directly, without
                    # also requiring the strategy's surface check: HubSpot stores the message server-
                    # side (POST 200 to .../thread/visitor/create) but its widget re-renders before a
                    # dom_echo can see the bubble, which false-negatived a real delivery. ack_http is
                    # only ever populated for a vendor that sets ack_response_re, so this is a no-op
                    # for the token/dom_echo vendors that reach this loop.
                    if ack_http:
                        return SendResult(True, self._ack_receipt(ack_http, ack_ws)[1])
                    if self._confirmed(page, surface, frames, token, ack_ws):
                        ok, det = self._ack_receipt(ack_http, ack_ws)
                        return SendResult(True, det or "delivered")
                    page.wait_for_timeout(250)
                # Tail re-check: wait_for_timeout is what pumps the sync driver, so a receipt arriving
                # during the FINAL wait is captured but never re-tested by the top-of-loop check.
                # Re-check once before giving up (ADR-0009 false-negative fix).
                if ack_http:
                    return SendResult(True, self._ack_receipt(ack_http, ack_ws)[1])
                if self._confirmed(page, surface, frames, token, ack_ws):
                    ok, det = self._ack_receipt(ack_http, ack_ws)
                    return SendResult(True, det or "delivered")
                if prechat_blocked:
                    return SendResult(False, "prechat_blocked_required_fields")
                return SendResult(False, "no_delivery_confirmation")
            except Exception as e:
                # Deliver-then-raise: if the Pitch already hit the wire, report it honestly so the
                # Ledger advances and we never re-pitch (double-send). Consult the server receipt FIRST
                # (dom_echo confirm can't see an HTTP 201; ADR-0009 fix), then the strategy confirm.
                # page may be unbound if the failure was during launch/context, before it was set.
                _ok, _det = self._ack_receipt(ack_http, ack_ws)
                if _ok:
                    return SendResult(True, _det)
                if page is not None and self._confirmed(page, surface, frames, token, ack_ws):
                    return SendResult(True, "delivered_then_error")
                return SendResult(False, f"{type(e).__name__}: {str(e)[:160]}")
            finally:
                if netlog:
                    self._dump_netlog(netlog, domain, net_responses, recv_frames, frames)
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass

    # ----- CW_NETLOG spike: capture the real server ACK on the wire ----------------------

    def _attach_netcapture(self, page, responses, recv):
        """Record server HTTP responses (form-POST acks) and server->client websocket frames
        (chat acks) so we can SEE what a genuine delivery ACK looks like, instead of inferring
        from what WE sent. Env-guarded (CW_NETLOG); no effect on normal runs."""
        def _cap(r):
            try:
                req = r.request
                method = req.method
                rt = req.resource_type
                # Capture EVERY non-GET (form/api submit of any resource_type, incl. navigations),
                # plus vendor-relevant xhr/fetch GETs. The request body is the smoking gun: if our
                # pitch text never leaves the browser in any request, the send did not transmit.
                if method == "GET" and rt not in ("xhr", "fetch"):
                    return
                e = {"method": method, "status": r.status, "type": rt, "url": r.url[:220]}
                if method != "GET":
                    try:
                        e["req_body"] = (req.post_data or "")[:1400]
                    except Exception:
                        pass
                    try:
                        e["resp_body"] = r.text()[:900]
                    except Exception:
                        pass
                responses.append(e)
            except Exception:
                pass
        page.on("response", _cap)
        page.on("websocket",
                lambda ws: ws.on("framereceived",
                                 lambda pl: recv.append(pl[:600] if isinstance(pl, str) else "<bin>")))

    def _dump_netlog(self, netlog, domain, responses, recv, sent):
        try:
            import json as _json
            safe = "".join(c if c.isalnum() else "_" for c in (domain or "x"))
            with open(f"{netlog}/net_{safe}.json", "w") as f:
                _json.dump({
                    "domain": domain,
                    "responses": responses,
                    "recv_frames": recv[-150:],
                    "sent_frames": [str(x)[:600] for x in sent],
                }, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def _frame_ack(ack_ws, token):
        """A captured server frame carries OUR Pitch token = the vendor stored our message. Used by
        Chatra, whose DDP layer echoes a stored visitor message back as a 'Messages added ...
        message:<pitch>' frame; the token scope is what makes it ours and not a bot/system frame that
        merely shares the Messages collection. Token matched raw OR JSON-escaped (SockJS wraps the
        frame, so an embedded quote/backslash in the pitch arrives escaped)."""
        if not token or not ack_ws:
            return False
        esc = json.dumps(token)[1:-1]
        return any(isinstance(f, str) and (token in f or (esc and esc in f)) for f in ack_ws)

    @staticmethod
    def _ack_receipt(ack_http, ack_ws):
        """Turn captured server receipts into (delivered, detail). A ws frame carries a server id
        (Tidio: [true,{"id":N}]); an HTTP receipt carries its status (Help Scout: 201). Detail records
        the proof so the Ledger keeps the server's own reference."""
        if ack_ws:
            m = re.search(r'"id":\s*(\d+)', ack_ws[-1])
            return True, f"delivered_ack:{m.group(1) if m else 'ws'}"
        if ack_http:
            return True, f"delivered_ack:{ack_http[-1][0]}"
        return False, ""

    # ----- surface + confirm ------------------------------------------------------------

    def _surface(self, page):
        """The Page or Frame the composer lives on. A widget that renders in an iframe is resolved
        either by a substring of the iframe URL (widget_frame_url, e.g. livechatinc.com / chatra.io)
        or, when the iframe has no stable URL (Tawk's about:srcdoc), by an in-frame content selector
        (widget_frame_marker). Otherwise the page. Waits briefly because the frame appears after the
        widget opens."""
        marker = self.config.widget_frame_marker
        url_sub = self.config.widget_frame_url
        if not marker and not url_sub:
            return page
        comp = self._scoped(self.config.widget_scope, self.config.composer_selector)
        for _ in range(24):  # heavy stores render the widget iframe slowly; wait up to ~12s
            candidates = self._candidate_frames(page, marker, url_sub)
            # When several frames match (HelpScout renders two Beacon iframes), prefer the one that
            # actually holds the composer.
            for fr in candidates:
                try:
                    if fr.locator(comp).count() > 0:
                        return fr
                except Exception:
                    continue
            if candidates:
                return candidates[0]
            try:
                page.wait_for_timeout(500)
            except Exception:
                break
        return page  # frame never appeared -> composer lookup fails -> no_composer (retryable)

    def _candidate_frames(self, page, marker, url_sub):
        """Frames that could be the widget iframe, gathered from TWO sources and deduped. HEADLESS
        Chromium does NOT attach about:srcdoc iframes (Tawk's v4 panel) to page.frames - it lists only
        real-URL frames - so a marker-based lookup over page.frames alone finds nothing headless and
        Tawk fell to no_composer on every store (the 0/11 regression). We ALSO walk the <iframe> DOM
        elements and resolve each via content_frame(), which DOES return the srcdoc frame headless. A
        frame qualifies by matching the url substring (LiveChat/Chatra) or by carrying the in-frame
        marker (Tawk/Help Scout)."""
        seen = set()
        out = []

        def consider(fr):
            if fr is None or fr == page.main_frame or id(fr) in seen:
                return
            seen.add(id(fr))
            try:
                if (url_sub and url_sub in (fr.url or "")) or \
                   (marker and fr.locator(marker).count() > 0):
                    out.append(fr)
            except Exception:
                pass

        try:
            for fr in page.frames:
                consider(fr)
        except Exception:
            pass
        try:
            for h in page.query_selector_all("iframe"):   # catches srcdoc frames page.frames omits
                try:
                    consider(h.content_frame())
                except Exception:
                    continue
        except Exception:
            pass
        return out

    def _confirmed(self, page, surface, frames, token, ack_ws=None):
        """Was the Pitch really sent?
        wire_token  : with a server receipt (ack_frame_re) and ack_ws supplied, require the SERVER's
                      ack frame (ADR-0009); otherwise a marker websocket frame WE sent carries the
                      token (Tidio; ADR-0003).
        callback_flag: the vendor's visitor-message callback recorded our token to window.__cw_confirm.
        dom_echo    : our token now appears in the rendered conversation AND the composer has cleared
                      (Tawk). The composer-empty clause is what distinguishes a sent message from the
                      token merely sitting un-sent in the composer, so it never false-positives."""
        cs = self.config.confirm_strategy
        if cs == "wire_token":
            if self.config.ack_frame_re and ack_ws is not None:
                return bool(ack_ws)          # the SERVER sent a matching "got it" receipt
            return self._delivered(frames, token, self.config.confirm_frame_marker)
        if cs == "callback_flag":
            try:
                blob = page.evaluate("() => (window.__cw_confirm || []).join('\\n')")
            except Exception:
                return False
            return bool(blob) if not token else (token in blob)
        if cs == "dom_echo":
            if surface is None or not token:
                return False
            try:
                shown = surface.evaluate(
                    "() => (document.body && document.body.innerText) || ''")
                comp = self._composer(surface)
                composer_empty = True
                if comp is not None:
                    val = comp.evaluate("el => (el.value != null ? el.value : (el.textContent || ''))")
                    composer_empty = not (val or "").strip()
            except Exception:
                return False
            return (token in shown) and composer_empty
        return False

    def _handle_email_gate(self, surface, page, frames, token, reply_email) -> bool:
        """Get past the email gate. Returns True if a required pre-chat field still blocks Send.

        "none": no gate. "prechat_then_api": if a pre-chat email field is visible, fill it (and any
        required name) and click Send, nudging a resend if the wire frame has not flushed; otherwise
        attach the email through the vendor API so the operator can still reply.
        """
        cfg = self.config
        if cfg.email_strategy in ("none", "contact_form", "composer_intro"):
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
            if not self._confirmed(page, surface, frames, token):
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
            if not self._confirmed(page, surface, frames, token):
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

    # ----- contact-form family (LiveChat offline / Help Scout "Ask"): a multi-field FORM that
    #        must be filled and SUBMITTED, not a chat thread that echoes ------------------------

    _ROLE_SELECTORS = {
        "name": ("input[name*='name' i], input[id*='name' i], "
                 "input[placeholder*='name' i], input[aria-label*='name' i]"),
        "email": ("input[type='email'], input[name*='email' i], input[id*='email' i], "
                  "input[placeholder*='email' i], input[aria-label*='email' i]"),
        "subject": ("input[name*='subject' i], input[id*='subject' i], "
                    "input[placeholder*='subject' i], input[aria-label*='subject' i]"),
    }
    _FORM_SUCCESS = ("thank", "get back to you", "we'll get back", "we will get back",
                     "received your message", "message sent", "we got your", "be in touch",
                     "talk soon", "we'll reply", "message has been sent", "your message has been")

    def _is_contact_form(self, surface):
        """True if the surface is a leave-a-message FORM (an email input AND a submit-ish button),
        not a live chat composer. Lets a contact_form vendor fall back to the normal chat send when
        the store is ONLINE (a live composer, with no email field / submit button)."""
        try:
            has_email = surface.locator(
                self._scoped(self.config.widget_scope, self._ROLE_SELECTORS["email"])).count() > 0
            return bool(has_email and self._form_submit_locator(surface) is not None)
        except Exception:
            return False

    def _offline_form_message_field(self, surface):
        """A leave-a-message form's MESSAGE field: a textarea whose name/placeholder/aria says
        'message', else the first visible textarea (Tawk's offline message box has no identifying
        attrs). Its presence is what distinguishes an OFFLINE ticket form (has a message field) from a
        pre-chat Start-Chat gate (Name/Email/Phone, no message), so we never mistake one for the
        other."""
        named = ("textarea[name*='message' i], textarea[placeholder*='message' i], "
                 "textarea[aria-label*='message' i], textarea[id*='message' i]")
        try:
            loc = surface.locator(self._scoped(self.config.widget_scope, named)).first
            if loc.count() and loc.is_visible(timeout=600):
                return loc
        except Exception:
            pass
        try:
            tas = surface.locator(self._scoped(self.config.widget_scope, "textarea"))
            for i in range(min(tas.count(), 6)):
                el = tas.nth(i)
                if el.is_visible(timeout=400):
                    return el
        except Exception:
            pass
        return None

    def _submit_contact_form(self, surface, page, composer, pitch, reply_email, debug, ack_http=None):
        """Fill message + name + email + subject, click the form's submit, then confirm it actually
        went through. With a server receipt (ack_response_re, Help Scout) delivery requires a POST 2xx
        to the vendor's conversation endpoint - a submitted-looking form with NO such receipt is
        form_no_server_ack, never delivered (ADR-0009). Without one (LiveChat, for now) it falls back
        to the thank-you/form-replaced DOM signal (form_submitted), never a still-showing form."""
        try:
            self._enter_text(composer, pitch)         # message (real keystrokes when required)
        except Exception:
            pass
        self._fill_role(surface, "name", "Nikhil")
        self._fill_role(surface, "email", reply_email)
        self._fill_role(surface, "subject", "8 email flows to lift your conversions")
        submit = self._form_submit_locator(surface)
        if os.environ.get("CW_FORMDUMP"):
            self._formdump(surface, submit, "after-fill")
        if submit is None:
            return SendResult(False, "form_no_submit")
        try:
            submit.click(timeout=4000, force=True)
        except Exception:
            try:
                submit.evaluate("el => el.click()")
            except Exception:
                return SendResult(False, "form_submit_failed")

        def _shot():
            if debug:
                try:
                    page.screenshot(path="/tmp/tidio_dbg_sent.png")
                except Exception:
                    pass

        time.sleep(2)
        _shot()
        if os.environ.get("CW_FORMDUMP"):
            self._formdump(surface, submit, "after-submit")
        use_ack = bool(self.config.ack_response_re)
        deadline = time.time() + 8
        while time.time() < deadline:
            if use_ack:
                if ack_http:                         # server stored the conversation (POST 2xx)
                    _shot()
                    return SendResult(True, f"delivered_ack:{ack_http[-1][0]}")
            elif self._form_confirmed(surface):
                _shot()
                return SendResult(True, "form_submitted")
            page.wait_for_timeout(300)
        # Tail re-check: a receipt captured during the final wait_for_timeout (ADR-0009 fix).
        if use_ack and ack_http:
            _shot()
            return SendResult(True, f"delivered_ack:{ack_http[-1][0]}")
        if not use_ack and self._form_confirmed(surface):
            _shot()
            return SendResult(True, "form_submitted")
        return SendResult(False, "form_no_server_ack" if use_ack else "form_unconfirmed")

    def _enter_text(self, locator, value):
        """Put text into a field. Default is .fill() (fast). For a vendor flagged fill_by_keystroke
        (Help Scout Beacon v2), .fill()'s synthetic input event does NOT reach the controlled input's
        state, so the form validates as empty and never submits; real per-key typing does commit it."""
        if self.config.fill_by_keystroke:
            try:
                locator.click(timeout=3000)
            except Exception:
                pass
            try:
                locator.fill("", timeout=3000, force=True)          # clear any prior text
            except Exception:
                pass
            locator.press_sequentially(value, delay=8, timeout=15000)
        else:
            locator.fill(value, timeout=4000, force=True)

    def _fill_role(self, surface, role, value):
        """Fill the first visible input matching a role (name/email/subject). Subject falls back to a
        required text input that is neither name nor email (LiveChat uses a build-hashed subject id)."""
        try:
            loc = surface.locator(
                self._scoped(self.config.widget_scope, self._ROLE_SELECTORS[role])).first
            if loc.count() and loc.is_visible(timeout=1000):
                self._enter_text(loc, value)
                return True
        except Exception:
            pass
        if role == "subject":
            return self._fill_orphan_required_text(surface, value)
        return False

    def _fill_orphan_required_text(self, surface, value):
        """Fill an empty required text input that is neither the name nor the email field."""
        try:
            inputs = surface.locator(self._scoped(self.config.widget_scope, "input[type='text']"))
            for i in range(min(inputs.count(), 10)):
                el = inputs.nth(i)
                try:
                    meta = el.evaluate("e => ((e.name||'')+' '+(e.id||'')+' '+(e.placeholder||'')+"
                                       "' '+(e.getAttribute('aria-label')||'')).toLowerCase()")
                    required = el.evaluate(
                        "e => e.required || e.getAttribute('aria-required')==='true'")
                    val = el.evaluate("e => e.value || ''")
                except Exception:
                    continue
                if not required or "name" in meta or "email" in meta or (val or "").strip():
                    continue
                if el.is_visible(timeout=500):
                    self._enter_text(el, value)
                    return True
        except Exception:
            pass
        return False

    def _formdump(self, surface, submit, when):
        """CW_FORMDUMP diagnostic: what our fill actually populated + which button we'd click +
        any validation alerts, read live off the surface. Env-guarded; no effect on normal runs."""
        try:
            state = surface.evaluate('''() => ({
              inputs: [...document.querySelectorAll('input,textarea')].filter(e=>e.type!=='hidden')
                .map(e=>({field:(e.name||e.id||'').slice(0,20), type:e.type, req:!!e.required,
                          val:(e.value||'').slice(0,30), invalid:e.getAttribute('aria-invalid')})),
              alerts: [...document.querySelectorAll("[role='alert'],[aria-live],[class*='error' i],[class*='alert' i]")]
                .map(e=>(e.innerText||'').replace(/\\s+/g,' ').trim()).filter(Boolean).slice(0,6)
            })''')
            btn = None
            if submit is not None:
                try:
                    btn = submit.evaluate("e=>(e.innerText||e.value||'').replace(/\\s+/g,' ').slice(0,30)")
                except Exception:
                    btn = "<err>"
            print(f"[CW_FORMDUMP {when}] submit={btn!r} inputs={state['inputs']} alerts={state['alerts']}",
                  flush=True)
        except Exception as e:
            print(f"[CW_FORMDUMP {when}] err {e!r}", flush=True)

    def _form_submit_locator(self, surface):
        """The form's REAL send button. Help Scout's Beacon renders attach (image-plus) + emoji as
        type=submit buttons that sit BEFORE the real 'Send a message', so taking the first submit
        clicks the attach control and nothing sends. Instead we score every visible button, drop
        icon/nav controls (attach/emoji/back/close/...), and prefer explicit send-intent text, then a
        real submit, then longest text. Submit text is store-customizable (seen: 'Hit us up'). We tag
        the winner with a data attr and locate by it, so an index can't drift past invisible buttons."""
        try:
            sel = surface.evaluate('''(scope) => {
              const root = scope ? (document.querySelector(scope) || document) : document;
              const bad = /attach|emoji|image-plus|image|photo|upload|file|back|close|minimi|menu|expand|sound|settings|mute|record/i;
              const send = /send|submit|hit us up|get in touch|continue|start chat|message/i;
              const btns = Array.from(root.querySelectorAll("button, input[type='submit'], [role='button']"))
                .filter(b => { const r=b.getBoundingClientRect(); return r.width>0 && r.height>0; });
              const label = b => ((b.innerText||b.value||'') + ' ' + (b.getAttribute('aria-label')||'')).trim();
              let best=null, bestScore=-1;
              btns.forEach(b => {
                const t = label(b);
                if(!t || bad.test(t)) return;
                let score = t.length;
                if(send.test(t)) score += 1000;                                   // explicit send intent
                if((b.getAttribute('type')||'').toLowerCase()==='submit') score += 100;  // a real submit
                if(score>bestScore){ bestScore=score; best=b; }
              });
              if(!best) return null;
              best.setAttribute('data-cw-submit','1');
              return "[data-cw-submit='1']";
            }''', self.config.widget_scope or "")
            if sel:
                loc = surface.locator(sel).first
                if loc.count() and loc.is_visible(timeout=800):
                    return loc
        except Exception:
            pass
        return None

    def _form_confirmed(self, surface):
        """A form send is confirmed only on a success SIGNAL: a thank-you / we'll-get-back phrase,
        or the whole form was replaced (both the submit control AND the email field are gone). A form
        still showing its submit button (e.g. a validation error) is NOT confirmed - stays honest."""
        try:
            txt = (surface.evaluate(
                "(scope) => { const r = scope ? (document.querySelector(scope) || document.body) "
                ": document.body; return (r && r.innerText) || ''; }",
                self.config.widget_scope or "") or "").lower()
        except Exception:
            return False
        if any(p in txt for p in self._FORM_SUCCESS):
            return True
        try:
            submit_gone = self._form_submit_locator(surface) is None
            email_gone = surface.locator(
                self._scoped(self.config.widget_scope, self._ROLE_SELECTORS["email"])).count() == 0
            return submit_gone and email_gone
        except Exception:
            return False

    # ----- composer-intro gate (Chatra): the message is held "unsent, please introduce yourself"
    #        until a name (then email) is typed into the SAME composer -------------------------------

    def _finish_composer_intro(self, surface, page, pitch, reply_email, debug, ack_ws=None):
        """Chatra holds a visitor message as 'unsent, please introduce yourself' until the visitor
        types a name (then email) into the composer, which is repurposed for the intro. Fill it so
        the held message flushes, then confirm delivery. Prefer the SERVER receipt (ADR-0009): a
        captured 'Messages added ... message:<pitch>' frame carrying our token = Chatra stored our
        text (it does so even while the team is offline). Fall back to the DOM signal (our message in
        the thread AND the unsent flag gone) when no ws receipt was captured."""
        token = self._pitch_token(pitch)

        def _shot():
            if debug:
                try:
                    page.screenshot(path="/tmp/tidio_dbg_sent.png")
                except Exception:
                    pass

        for role, value in (("name", "Nikhil"), ("email", reply_email)):
            if not self._intro_pending(surface):
                break
            fld = None
            for _ in range(8):          # the intro input renders a few seconds after the held message
                fld = self._intro_input(surface, role)
                if fld is not None:
                    break
                page.wait_for_timeout(700)
                surface = self._surface(page)
            if fld is None:
                if role == "name":
                    break               # no name field ever appeared - cannot introduce
                continue
            try:
                fld.click()
                fld.fill(value, timeout=4000, force=True)
                fld.press("Enter")
            except Exception:
                pass
            time.sleep(2.5)
            surface = self._surface(page)
        # The intro form has its own Submit button; filling + Enter is not enough to send it.
        self._click_intro_submit(surface)
        time.sleep(2.5)
        surface = self._surface(page)
        _shot()
        deadline = time.time() + 6
        while time.time() < deadline:
            if self._frame_ack(ack_ws, token):     # server stored our message (the real receipt)
                _shot()
                return SendResult(True, "delivered_ack:chatra")
            if self._intro_delivered(surface, token):
                _shot()
                return SendResult(True, "delivered")
            surface = self._surface(page)
            page.wait_for_timeout(300)
        # Tail re-check: a receipt captured during the final wait_for_timeout (ADR-0009 fix). The
        # message can be stored server-side even if the intro form never fully rendered, so the ws
        # receipt is authoritative over the DOM.
        if self._frame_ack(ack_ws, token):
            _shot()
            return SendResult(True, "delivered_ack:chatra")
        return SendResult(False, "intro_unconfirmed")

    def _visible_textarea(self, surface):
        """The first visible textarea / contenteditable on the surface (Chatra's composer, reused
        for the intro)."""
        loc = surface.locator("textarea, [contenteditable='true']")
        try:
            for i in range(min(loc.count(), 6)):
                el = loc.nth(i)
                if el.is_visible(timeout=800):
                    return el
        except Exception:
            pass
        return None

    def _intro_input(self, surface, role):
        """The Chatra intro field for a role. After a held message Chatra reveals a small form with
        a 'Name' then (sometimes) an 'Email' input; scoped to the widget frame so a page-level
        newsletter field is never touched."""
        sel = {
            "name": "input[placeholder*='name' i], input[name*='name' i], input[aria-label*='name' i]",
            "email": "input[type='email'], input[placeholder*='email' i], input[name*='email' i]",
        }[role]
        try:
            loc = surface.locator(sel).first
            if loc.count() and loc.is_visible(timeout=1500):
                return loc
        except Exception:
            pass
        return None

    @staticmethod
    def _surface_text(surface):
        try:
            return surface.evaluate("() => (document.body && document.body.innerText) || ''") or ""
        except Exception:
            return ""

    def _intro_pending(self, surface):
        """True while Chatra still holds the message (the 'unsent' flag under our bubble)."""
        return "unsent" in self._surface_text(surface).lower()

    def _intro_delivered(self, surface, token):
        """Delivered = our message is in the thread AND it is no longer flagged 'unsent'. The bot's
        'Introduce yourself...' line lingers in the chat log even after the intro is saved, so we key
        on the 'unsent' hold flag - not the word 'introduce' - to avoid a false negative."""
        txt = self._surface_text(surface)
        return bool(token) and (token in txt) and ("unsent" not in txt.lower())

    def _click_intro_submit(self, surface):
        """Click the Chatra intro form's Submit button (filling the fields + Enter does not send it)."""
        for loc in (surface.locator("button[type='submit'], input[type='submit']").first,
                    surface.locator(
                        "button", has_text=re.compile("submit|send|continue|start", re.I)).first):
            try:
                if loc.count() and loc.is_visible(timeout=800):
                    loc.click(timeout=4000, force=True)
                    return True
            except Exception:
                continue
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

    def _fill_prechat_and_start(self, surface, reply_email):
        """A pre-chat gate (Tawk 'custom widget'): required Name/Email/Phone inputs + a Start button
        that must be submitted before the composer renders. Fill and submit it. Returns False (no-op)
        when no such gate is present, so default-widget stores are untouched. Idempotent - once the
        form is submitted the composer replaces it and the email guard below fails on the next call."""
        try:
            email = surface.locator(self._ROLE_SELECTORS["email"]).first
            if not (email.count() and email.is_visible(timeout=800)):
                return False
        except Exception:
            return False
        start = self._prechat_start_button(surface)
        if start is None:
            return False
        self._fill_role(surface, "name", "Nikhil")
        self._fill_role(surface, "email", reply_email)
        self._fill_phone(surface)
        try:
            start.click(timeout=4000, force=True)
            return True
        except Exception:
            try:
                start.evaluate("el => el.click()")
                return True
            except Exception:
                return False

    def _prechat_start_button(self, surface):
        """The pre-chat (Start-Chat) form's start control. Deliberately does NOT match 'Submit': an
        offline 'leave a message' ticket form (Name/Email/Message + Submit) is a DIFFERENT widget
        state that must fill the message before submitting, so it is not treated as a pre-chat gate
        here (it stays no_composer until the offline-form path is built)."""
        pat = re.compile(r"start chat|start conversation|begin chat|chat now|let'?s chat|^\s*start\s*$", re.I)
        for sel in ("button", "[role='button']"):
            try:
                loc = surface.locator(sel, has_text=pat).first
                if loc.count() and loc.is_visible(timeout=500):
                    return loc
            except Exception:
                continue
        try:                                     # input[type=submit] carries its label in value, not text
            loc = surface.locator("input[type='submit']").first
            if loc.count() and loc.is_visible(timeout=500):
                return loc
        except Exception:
            pass
        return None

    def _fill_phone(self, surface):
        """Fill a required phone field if the pre-chat form has one (a tel input, or name/placeholder/
        aria 'phone'). A generic number; no-op when absent so non-phone forms are unaffected."""
        sel = ("input[type='tel'], input[name*='phone' i], input[id*='phone' i], "
               "input[placeholder*='phone' i], input[aria-label*='phone' i]")
        try:
            loc = surface.locator(sel).first
            if loc.count() and loc.is_visible(timeout=500):
                self._enter_text(loc, "2025550123")
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
    def _dump_form(surface):
        """Spike helper: dump the visible form controls on the surface (inputs/textareas/buttons)
        with their identifying attributes, so a contact-form handler can be built against the real
        DOM. Guarded by CW_DUMP; never runs in a normal send."""
        try:
            data = surface.evaluate('''() => Array.from(
                document.querySelectorAll("input,textarea,select,button,[role='button']")
              ).filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 || r.height > 0; })
               .map(el => ({
                 tag: el.tagName.toLowerCase(),
                 type: el.getAttribute('type') || '',
                 name: el.getAttribute('name') || '',
                 id: el.id || '',
                 ph: el.getAttribute('placeholder') || '',
                 aria: el.getAttribute('aria-label') || '',
                 req: el.hasAttribute('required') || el.getAttribute('aria-required') === 'true',
                 text: (el.innerText || '').trim().slice(0, 50)
               }))''')
            import json as _json
            return "[FORM_DUMP]\n" + "\n".join(_json.dumps(d) for d in data)
        except Exception as e:
            return f"[FORM_DUMP] failed: {e!r}"

    @staticmethod
    def _dismiss_site_overlays(page, use_escape=True, widget_scope=None):
        """Close page-level modals (newsletter/consent) that can obscure the widget's fields, scoped
        OUTSIDE the widget so we never close the chat itself. Escape clears a load-time modal but ALSO
        closes an already-open chat widget (Help Scout's Beacon binds Escape-to-close), so callers
        pass use_escape=False once the widget is open and rely on the targeted close-buttons below.
        The close-button sweep must also skip the WIDGET'S OWN close/minimize control: a page-DOM
        widget renders an aria-label like 'Close Chatbox' that matches *lose* and would shut the box we
        just opened (this closed Olark to no_composer). Exclude the active widget_scope from the sweep."""
        if use_escape:
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
        not_widget = ":not(#tidio-chat *)"
        if widget_scope:
            not_widget += f":not({widget_scope} *)"
        for sel in ['[class*="klaviyo" i] button[aria-label*="lose" i]',
                    'button[aria-label="Close dialog" i]', '[id*="onetrust-accept"]',
                    f'button[aria-label*="lose" i]{not_widget}']:
            try:
                loc = page.locator(sel).first
                if loc.count() and loc.is_visible(timeout=300):
                    loc.click(timeout=800)
            except Exception:
                continue
