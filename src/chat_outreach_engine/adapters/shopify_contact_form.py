"""ShopifyContactFormAdapter: deliver the Pitch through a store's native Shopify CONTACT FORM.

Second delivery door (equal to the chat widget, not a fallback of last resort): almost every Shopify
store has a Contact Us form that posts to `/contact` and lands in the owner's support inbox - through
THEIR own site, so it sidesteps our email deliverability problem. Spike (research/contact_form_spike.py)
showed the form is highly uniform (form_type=contact, `contact[email]` + a name input + a message
textarea) and MOSTLY CAPTCHA-FREE (7/8), unlike Shopify Inbox's silent hCaptcha.

Field names vary by theme (contact[body] / contact[Comment] / contact[Message]; contact[name] /
contact[Name]), so we classify fields by ROLE (the message is the textarea; the email is the email
input; the name is a name-ish input) rather than hardcoding names. Confirm by the Shopify success
signal: a redirect to `?contact_posted=true` or a "thanks, we'll get back to you" success message.

CAPTCHA REALITY (measured 2026-06-30, research/measure_contact_headed.py): Shopify's contact-form
spam protection is an INTERACTIVE hCaptcha - invisible at page load, then on submit it throws a
must-solve "pick the images" challenge to automated browsers. It is stricter than Shopify Inbox's
PASSIVE hCaptcha (which silently passes ~50% headless). Neither the residential proxy (changes IP) nor
a headed browser (changes fingerprint) bypasses it: 0/8 passed both ways. The only bypass is a paid
captcha solver, which Nikhil has ruled out. So this adapter delivers only the FREE (no-captcha) subset:
on submit, if the interactive hCaptcha appears it returns `captcha_challenge` and we SKIP the store
(never solve, never pay). The captcha-free subset submits normally.

One-way model: the Pitch (carrying mercwise.com + the cal link) goes in the message; the email field
carries our reply email so a reply reaches us. This is NOT cold email (ADR-0001 stands) - it is the
store's own on-site form, submitted in a browser like a visitor would.
"""
from __future__ import annotations

import os
import time

from ..injector import SendResult
from ..proxy import playwright_proxy

# The name that goes in the form's required name field (form metadata, NOT a signature in the message).
FROM_NAME = "Nikhil"

# Shopify stores expose the contact form at one of these; tried in order.
CONTACT_PATHS = ("/pages/contact", "/pages/contact-us", "/contact", "/contact-us", "/pages/contact_us")

_SUCCESS_PHRASES = ("contact_posted=true", "thanks for contacting", "we'll get back",
                    "we will get back", "message has been sent", "your message was sent",
                    "thank you for", "we have received", "successfully sent")


def _is_success(url: str, body_text: str) -> bool:
    """Shopify confirms a posted contact form by redirecting to ?contact_posted=true and rendering a
    thank-you message. True if either signal is present."""
    u = (url or "").lower()
    if "contact_posted=true" in u:
        return True
    t = (body_text or "").lower()
    return any(p in t for p in _SUCCESS_PHRASES if p != "contact_posted=true")


def _field_role(tag: str, name: str, input_type: str) -> str:
    """Classify a form field by ROLE so theme-specific names/casing don't matter.
    message = the textarea; email = an email input; phone = a tel/phone input; name = a name-ish input.
    Everything else is 'other' (extra required selects/inputs are handled best-effort at fill time)."""
    tag = (tag or "").lower()
    n = (name or "").lower()
    t = (input_type or "").lower()
    if tag == "textarea":
        return "message"
    if t == "email" or "email" in n:
        return "email"
    if t == "tel" or "phone" in n:
        return "phone"
    if "name" in n:
        return "name"
    return "other"


class ShopifyContactFormAdapter:
    vendor = "shopify-contact-form"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        from playwright.sync_api import sync_playwright

        headed = os.environ.get("HEADED", "").lower() in ("1", "true", "yes")
        with sync_playwright() as p:
            channel = os.environ.get("BROWSER_CHANNEL", "chrome") or None
            browser = p.chromium.launch(headless=not headed, channel=channel,
                                        args=["--disable-blink-features=AutomationControlled"])
            page = browser.new_context(
                viewport={"width": 1366, "height": 900}, locale="en-US",
                proxy=playwright_proxy(),
                user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
            ).new_page()
            try:
                form = self._find_form(page, domain)
                if form is None:
                    return SendResult(False, "no_contact_form")
                if not self._fill(form, pitch, reply_email):
                    return SendResult(False, "fill_failed")
                before_url = page.url
                self._submit(form, page)
                # Poll: Shopify's spam-protection hCaptcha is INVISIBLE until submit, so we can only
                # tell captcha-free (posts -> success) from captcha-gated (interactive challenge appears)
                # AFTER clicking. Give the success signal or the challenge time to render.
                deadline = time.time() + 8
                while time.time() < deadline:
                    body = ""
                    try:
                        body = page.evaluate("() => (document.body && document.body.innerText) || ''")
                    except Exception:
                        pass
                    if _is_success(page.url, body):
                        return SendResult(True, "delivered")
                    if self._captcha_visible(page):
                        # interactive hCaptcha - free subset only, we never solve/pay: skip it
                        return SendResult(False, "captcha_challenge")
                    time.sleep(1)
                # a required extra field (Reason/Order#) can silently block submit
                if page.url == before_url and self._has_unfilled_required(form):
                    return SendResult(False, "form_blocked_required_fields")
                return SendResult(False, "no_confirmation")
            except Exception as e:
                return SendResult(False, f"{type(e).__name__}: {str(e)[:160]}")
            finally:
                try:
                    browser.close()
                except Exception:
                    pass

    # ----- live helpers -----------------------------------------------------------------

    def _find_form(self, page, domain):
        """Return a Locator for the contact form (email input + textarea), trying the usual paths."""
        base = domain if domain.startswith("http") else "https://" + domain
        for path in CONTACT_PATHS:
            try:
                resp = page.goto(base + path, wait_until="domcontentloaded", timeout=30000)
                if resp and resp.status >= 400:
                    continue
                time.sleep(1.2)
                forms = page.locator("form")
                for i in range(min(forms.count(), 8)):
                    f = forms.nth(i)
                    has_email = f.locator("input[type='email'], input[name*='email' i]").count() > 0
                    has_ta = f.locator("textarea").count() > 0
                    if has_email and has_ta and f.is_visible(timeout=1000):
                        return f
            except Exception:
                continue
        return None

    def _captcha_visible(self, page) -> bool:
        """A VISIBLE, sizeable hCaptcha/reCAPTCHA challenge on the page after submit (the interactive
        wall). Shopify's spam-protection iframe is present-but-hidden until the challenge fires, so we
        require real visibility + size, not mere presence, to avoid false positives on the passive case."""
        try:
            return page.evaluate(
                "() => { const q = document.querySelectorAll(\"iframe[src*='hcaptcha'], "
                "iframe[title*='captcha' i], .h-captcha, iframe[src*='recaptcha']\");"
                " for (const e of q) { try { if (e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})"
                " && (e.offsetWidth>80 || e.offsetHeight>80)) return true; } catch(_) { if (e.offsetWidth>80) return true; } }"
                " return false; }")
        except Exception:
            return False

    def _fill(self, form, pitch, reply_email) -> bool:
        """Fill by role: email input, first name-ish input, the message textarea. Best-effort on a
        required phone. Returns True if at least email + message got filled."""
        ok_email = ok_msg = False
        try:
            email = form.locator("input[type='email'], input[name*='email' i]").first
            if email.count():
                email.fill(reply_email, timeout=6000)
                ok_email = True
        except Exception:
            pass
        try:
            name = form.locator("input[name*='name' i]").first
            if name.count() and name.is_visible(timeout=800):
                name.fill(FROM_NAME, timeout=4000)
        except Exception:
            pass
        try:
            ta = form.locator("textarea").first
            if ta.count():
                ta.fill(pitch, timeout=6000)
                ok_msg = True
        except Exception:
            pass
        try:
            phone = form.locator("input[type='tel'], input[name*='phone' i]").first
            if phone.count() and phone.is_visible(timeout=500):
                phone.fill("0000000000", timeout=3000)
        except Exception:
            pass
        return ok_email and ok_msg

    def _submit(self, form, page):
        btn = form.locator("button[type='submit'], input[type='submit'], "
                           "button:has-text('Send'), button:has-text('Submit')").first
        try:
            if btn.count():
                btn.click(timeout=5000, force=True)
                return
        except Exception:
            pass
        try:
            form.evaluate("f => f.submit()")
        except Exception:
            pass

    def _has_unfilled_required(self, form) -> bool:
        try:
            return form.evaluate(
                "f => Array.from(f.querySelectorAll('[required]')).some(e => !e.value)")
        except Exception:
            return False
