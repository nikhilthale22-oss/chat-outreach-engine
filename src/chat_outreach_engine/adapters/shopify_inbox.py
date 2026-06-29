"""ShopifyInboxAdapter: Adapter for the Shopify Inbox storefront chat (the count-leader vendor, ~49k).

Its OWN class, not a WidgetDriver config: the flow diverges from the DOM-drive family (ADR-0007's
"different control flow -> its own class"). Shopify Inbox renders <inbox-online-store-chat> with an
OPEN shadow DOM (Playwright CSS pierces it), and the send flow is:
    open the widget -> type into the composer -> click Send -> a "Before we get started" contact
    FORM (First Name / Last Name / Email) appears -> Start chat -> the message posts to the thread.
The script is JS-injected, so the static SignatureDetector misses Shopify Inbox; this adapter does its
own browser-layer liveness check (poll for the <inbox-online-store-chat> element) and returns
no_shopify_inbox if it never appears.

UNLOCKED 2026-06-29 (research/shopify-inbox-injection.md). The contact form is footer-labelled
"protected by hCaptcha", but that hCaptcha is INVISIBLE/PASSIVE: a real send from a HEADLESS browser
on a DATACENTER IP posted with NO challenge. So Shopify Inbox IS automatable, free (no captcha solver
at low volume). Bonus: the form REQUIRES an email, so it is the one vendor with a built-in reply path
(the merchant's reply emails back to the address we leave) - the others are email_strategy="none".

Honesty (the _verdict seam): send() returns delivered ONLY when the Pitch token actually appears in the
rendered thread ("You sent: ..."). If a VISIBLE hCaptcha challenge appears (passive scoring flagged the
session), it returns "captcha_challenge" so the batch routes around it instead of false-claiming a send.

Env: HEADED=1 real window; SI_DEBUG=1 screenshots to /tmp/si_dbg_*.png.
"""
from __future__ import annotations

import os
import time

from ..injector import SendResult
from ..proxy import playwright_proxy
from ..widget_driver import WidgetDriver

SCOPE = "inbox-online-store-chat"               # the custom element; Playwright CSS pierces its open shadow
COMPOSER = f"{SCOPE} textarea"
LAUNCHER = f"{SCOPE} [data-spec='toggle-button']"
SEND = f"{SCOPE} [data-spec='message-submit']"
SENDER_FIRST, SENDER_LAST = "Nikhil", "Thale"   # matches the Pitch signature
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# Read the inbox widget's open shadow tree: the rendered thread TEXT, whether a captcha challenge is
# VISIBLE, whether the contact form is still up. One evaluate so the verdict is taken from a single
# coherent snapshot. A textarea's typed value is NOT in textContent, so the Pitch appearing in the
# returned thread_text means it actually rendered in the thread (not sitting un-sent in the composer).
# Delivery is decided in Python (_thread_has_pitch), whitespace-insensitively, because the thread's
# textContent concatenates DOM nodes WITHOUT spaces and carries newlines/tabs - a byte-for-byte
# substring check against the source Pitch misses delivered messages (the submitted_unconfirmed bug).
_STATE_JS = r"""
() => {
  const inbox = document.querySelector('inbox-online-store-chat');
  const out = {present:false, composer_visible:false, challenge_visible:false,
               form_present:false, thread_text:''};
  if (!inbox || !inbox.shadowRoot) return out;
  out.present = true;
  const els=[]; const v=(r)=>{try{r.querySelectorAll('*').forEach(e=>{els.push(e); if(e.shadowRoot) v(e.shadowRoot);});}catch(_){}}; v(inbox.shadowRoot);
  const tag=e=>(e.tagName||'').toLowerCase();
  for (const e of els) {
    if (tag(e)==='textarea') { try{const r=e.getBoundingClientRect(); if(r.width>40&&r.height>10) out.composer_visible=true;}catch(_){} }
    if (tag(e)==='input') { const ph=(e.getAttribute('placeholder')||'').toLowerCase(); if(ph.includes('name')||ph.includes('email')) out.form_present=true; }
    if (tag(e)==='iframe' && /hcaptcha/i.test(e.src||'')) { try{const r=e.getBoundingClientRect(); if(r.width>80&&r.height>80) out.challenge_visible=true;}catch(_){} }
  }
  out.thread_text = (inbox.shadowRoot.textContent || '').slice(0, 8000);
  return out;
}
"""


class ShopifyInboxAdapter:
    vendor = "shopify-inbox"

    # ----- pure verdict seam (unit-tested) ----------------------------------------------
    @staticmethod
    def _verdict(state: dict, submitted: bool) -> SendResult:
        """Map a shadow-state snapshot + whether we clicked Start chat to an honest SendResult.

        Order matters. A visible captcha challenge means passive scoring blocked us (NOT delivered).
        The Pitch signature in the rendered thread is the only POSITIVE proof of delivery. Then the
        anti-double-send rule: once we have clicked Start chat the message is irreversibly committed,
        so if it is unconfirmed we return submitted_unconfirmed - a TERMINAL detail (never retried),
        because re-pitching could double-send a real merchant. Only failures BEFORE submit (the form
        still up, or never reached) stay retryable, since nothing was committed."""
        if state.get("challenge_visible"):
            return SendResult(False, "captcha_challenge")
        if state.get("pitch_in_thread"):
            return SendResult(True, "delivered")
        if submitted:
            return SendResult(False, "submitted_unconfirmed")
        if state.get("form_present"):
            return SendResult(False, "form_blocked")
        return SendResult(False, "no_delivery_confirmation")

    @staticmethod
    def _match_key(pitch: str) -> str:
        """A distinctive, WHITESPACE-FREE slice from the start of the Pitch - the key we look for in the
        rendered thread. Whitespace-stripped (not just normalised to spaces) because the thread's
        textContent joins DOM nodes with no spaces; a 32-char run from the Pitch opening is long enough
        to be unique to us yet survives any wrap/node-split. Empty Pitch -> empty key (never matches)."""
        return "".join((pitch or "").split())[:32]

    @staticmethod
    def _thread_has_pitch(thread_text: str, pitch: str) -> bool:
        """Did our Pitch actually render in the thread? Compare whitespace-insensitively: strip ALL
        whitespace from both sides, then substring-check the Pitch's match key. This recovers delivered
        messages the old space-joined check missed (the submitted_unconfirmed bucket), while a short
        shared word like "interested" still cannot confirm (the key is a 32-char run from the opening)."""
        key = ShopifyInboxAdapter._match_key(pitch)
        if not key:
            return False
        return key in "".join((thread_text or "").split())

    @staticmethod
    def _plan_form_values(fields: list, first: str, last: str, email: str) -> list:
        """Decide what to type into each contact-form field, locale-robustly. fields is a list of
        {type, placeholder, name} (document order). Returns a parallel list of values (None = leave
        blank). The email field is found by type=='email' OR a 'mail' keyword in type/placeholder/name
        (some stores render it as type=text, and 'mail' survives most locales). The remaining fields are
        name fields, filled by POSITION not by English label: one -> full name, two+ -> first then last.
        This is a strict superset of the old English-placeholder fill, so the proven form still fills the
        same way while non-English / variant forms now submit instead of stalling (form_blocked)."""
        vals = [None] * len(fields)
        email_idx = None
        for i, f in enumerate(fields):
            blob = " ".join([(f.get("type") or ""), (f.get("placeholder") or ""),
                             (f.get("name") or "")]).lower()
            if (f.get("type") or "").lower() == "email" or "mail" in blob:
                email_idx = i
                break
        if email_idx is not None:
            vals[email_idx] = email
        name_idxs = [i for i in range(len(fields)) if i != email_idx]
        if len(name_idxs) == 1:
            vals[name_idxs[0]] = f"{first} {last}".strip()
        else:
            for i, val in zip(name_idxs, [first, last]):
                vals[i] = val
        return vals

    # ----- live send (integration; proven by a real delivered message) ------------------
    def send(self, domain: str, pitch: str, reply_email: str, dry_run: bool = False) -> SendResult:
        from playwright.sync_api import sync_playwright

        headed = os.environ.get("HEADED", "").lower() in ("1", "true", "yes")
        debug = bool(os.environ.get("SI_DEBUG"))
        url = WidgetDriver._target_url(domain)

        def shot(page, name):
            if debug:
                try:
                    page.screenshot(path=f"/tmp/si_dbg_{name}.png")
                except Exception:
                    pass

        with sync_playwright() as p:
            browser = None
            try:
                channel = os.environ.get("BROWSER_CHANNEL", "chrome") or None
                browser = p.chromium.launch(
                    headless=not headed, channel=channel,
                    args=["--disable-blink-features=AutomationControlled"])
                page = browser.new_context(
                    viewport={"width": 1366, "height": 900}, locale="en-US",
                    proxy=playwright_proxy(), user_agent=_UA).new_page()

                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                # Browser-layer liveness: the script injects via JS, so poll for the element.
                if not self._wait_for_inbox(page):
                    return SendResult(False, "no_shopify_inbox")
                try:
                    page.keyboard.press("Escape")     # dismiss marketing popups
                except Exception:
                    pass

                if not self._open(page):
                    return SendResult(False, "no_launcher")
                composer = page.locator(COMPOSER).first
                try:
                    composer.wait_for(state="visible", timeout=10000)
                except Exception:
                    return SendResult(False, "no_composer")
                shot(page, "1_composer")
                if dry_run:
                    return SendResult(True, "composer_reached")

                composer.fill(pitch)                  # textarea: set the whole multi-line Pitch at once
                time.sleep(0.4)
                if not self._click_send(page, composer):
                    return SendResult(False, "no_send_button")
                time.sleep(3)
                shot(page, "2_form")

                submitted = self._fill_contact_form(page, reply_email)
                shot(page, "3_started")

                # Confirm: poll the rendered thread for our Pitch (delivered) or a visible challenge.
                # Delivery is decided whitespace-insensitively in Python. Once submitted, the verdict is
                # terminal either way (no re-pitch).
                deadline = time.time() + 14
                state = {}
                while time.time() < deadline:
                    state = page.evaluate(_STATE_JS)
                    state["pitch_in_thread"] = self._thread_has_pitch(state.get("thread_text", ""), pitch)
                    if state.get("pitch_in_thread") or state.get("challenge_visible"):
                        break
                    page.wait_for_timeout(500)
                shot(page, "4_final")
                # Diagnostic: when we committed (clicked Start chat) but did not confirm, dump the thread
                # text so the next live run shows WHY - delivered-but-mismatched vs genuinely not posted.
                if debug and submitted and not state.get("pitch_in_thread"):
                    try:
                        with open(f"/tmp/si_dbg_unconfirmed_{domain}.txt", "w") as fh:
                            fh.write(state.get("thread_text", ""))
                    except Exception:
                        pass
                return self._verdict(state, submitted)
            except Exception as e:
                return SendResult(False, f"{type(e).__name__}: {str(e)[:140]}")
            finally:
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass

    # ----- steps ------------------------------------------------------------------------
    @staticmethod
    def _wait_for_inbox(page) -> bool:
        for _ in range(20):                            # ~12s; the script injects via JS after load
            try:
                if page.evaluate("() => !!document.querySelector('inbox-online-store-chat')"):
                    return True
            except Exception:
                pass
            page.wait_for_timeout(600)
        return False

    @staticmethod
    def _open(page) -> bool:
        """Open the widget. Prefer the stable data-spec toggle; fall back to the first button inside
        the inbox shadow (the launcher)."""
        try:
            loc = page.locator(LAUNCHER).first
            if loc.count():
                loc.click(timeout=6000)
                return True
        except Exception:
            pass
        try:
            return bool(page.evaluate("""() => {
              const x=document.querySelector('inbox-online-store-chat'); if(!x||!x.shadowRoot) return false;
              const e=[]; const v=(r)=>{r.querySelectorAll('*').forEach(n=>{e.push(n); if(n.shadowRoot) v(n.shadowRoot);});}; v(x.shadowRoot);
              const b=e.find(n=>(n.tagName||'').toLowerCase()==='button'); if(b){ try{b.click(); return true;}catch(_){} } return false;
            }"""))
        except Exception:
            return False

    @staticmethod
    def _click_send(page, composer) -> bool:
        try:
            loc = page.locator(SEND).first
            if loc.count():
                loc.click(timeout=4000)
                return True
        except Exception:
            pass
        try:
            page.locator(SCOPE).get_by_role("button", name="Send").first.click(timeout=4000)
            return True
        except Exception:
            return False

    @staticmethod
    def _fill_contact_form(page, reply_email: str) -> bool:
        """Fill the post-send "Before we get started" form and click Start chat. Enumerates the form's
        VISIBLE inputs in document order, plans values locale-robustly (_plan_form_values), and fills by
        position - so non-English / variant forms submit instead of stalling. Returns True iff the submit
        button was actually clicked (the message is then committed - the caller uses this to make the
        result terminal and never double-send). Never raises."""
        scope = page.locator(SCOPE)
        inputs = scope.locator("input")
        fields, locs = [], []
        try:
            n = inputs.count()
        except Exception:
            n = 0
        for i in range(n):
            el = inputs.nth(i)
            try:
                if not el.is_visible():
                    continue
                fields.append({"type": el.get_attribute("type") or "",
                               "placeholder": el.get_attribute("placeholder") or "",
                               "name": el.get_attribute("name") or ""})
                locs.append(el)
            except Exception:
                continue
        for el, val in zip(locs, ShopifyInboxAdapter._plan_form_values(
                fields, SENDER_FIRST, SENDER_LAST, reply_email)):
            if val:
                try:
                    el.fill(val, timeout=4000)
                except Exception:
                    pass
        for name in ("Start chat", "Start Chat", "Continue", "Submit", "Send", "Begin", "Chat"):
            try:
                b = scope.get_by_role("button", name=name).first
                if b.count() and b.is_enabled(timeout=800):
                    b.click(timeout=4000)
                    return True
            except Exception:
                continue
        return False
