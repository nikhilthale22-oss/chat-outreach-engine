"""HelpScoutAdapter: Adapter for Help Scout Beacon widgets.

A VendorConfig over the shared WidgetDriver (ADR-0007). Reverse-engineered live: window.Beacon controls
the widget; Beacon('open') opens it and the "Ask" tab is a contact FORM (message textarea + email +
Send) rather than a live-chat composer. The widget renders in a same-origin about:blank iframe (no stable
URL), but that iframe has a STABLE id #beacon-container, so the driver resolves it by that content marker.

Probed open: Beacon('open') -> click "Ask" -> composer textarea (build-hashed class, so composer_selector
is the bare textarea) + an email field (a reply path).

STATUS: verified to the composer only. Because "Ask" is a FORM (fill message + email + click Send, then a
"thank you" state - not an echoed message), the full send + a form-submitted confirm is a follow-up;
email_strategy is "none" and confirm dom_echo for now (the verify-to-composer milestone).
"""
from __future__ import annotations

from ..injector import SendResult
from ..widget_driver import VendorConfig, WidgetDriver

HELPSCOUT = VendorConfig(
    vendor="helpscout",
    widget_scope=None,
    ready_predicate="window.Beacon",
    ready_fallback_predicate="window.Beacon",
    ready_timeout_ms=20000,
    not_ready_detail="no_beacon",
    # open AND navigate straight to the message form (Beacon's own router), so the composer textarea
    # renders without relying on clicking the "Ask" tab.
    open_js="window.Beacon('open'); window.Beacon('navigate', '/ask/message/')",
    entry_labels=("Ask", "Send a message", "Send us a message", "Email us", "Start a conversation"),
    # Help Scout's "Ask" tab is a contact FORM (name/subject/email/message + submit); the
    # contact_form path fills + submits it and confirms the thank-you state.
    email_strategy="contact_form",
    email_api_js=None,
    confirm_strategy="dom_echo",
    confirm_frame_marker=None,
    composer_selector="textarea",
    entry_strategy="by_text",
    widget_frame_marker="#beacon-container",
    # Server receipt (ADR-0009): Beacon files the "Ask" form as a POST to
    # beaconapi.helpscout.net/v1/<beacon>/conversations returning 201. Delivered only on that 2xx -
    # a submitted-looking form with no such POST (e.g. raincaper) is form_no_server_ack, not delivered.
    ack_response_re=r"helpscout\.net/.*/conversations",
    # Beacon v2 uses controlled inputs that ignore .fill()'s synthetic event and validate as empty;
    # real per-key typing is required for the form to submit at all (ADR-0010, proven on lowcostglasses).
    fill_by_keystroke=True,
)


class HelpScoutAdapter:
    vendor = "helpscout"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        return WidgetDriver(HELPSCOUT).send(domain, pitch, reply_email)
