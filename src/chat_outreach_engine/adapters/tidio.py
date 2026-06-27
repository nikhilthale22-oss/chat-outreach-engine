"""TidioAdapter: the Adapter for Tidio live-chat widgets.

Tidio is the DOM-drive family's reference vendor, so it is expressed as a VendorConfig (TIDIO)
over the shared WidgetDriver rather than as hand-written flow (ADR-0007). The reverse-engineering
that shapes the config (research/tidio-injection.md):

- Tidio's widget renders in OPEN SHADOW DOM under a single host, div#tidio-chat. Playwright pierces
  open shadow roots, so we scope every interaction to "#tidio-chat" - that keeps us on the widget
  and off the page's own forms (e.g. a Klaviyo newsletter with its own email field).
- messageFromVisitor()/messageFromOperator() are UI-simulation only; they do NOT transmit. The real
  path is to drive the widget like a visitor: open -> (Home) click an entry like "Chat with us" or
  the v4/Lyro "Chat with Lyro" -> type into the composer -> if a pre-chat form appears, fill the
  widget's email field and Send. The held message then flushes.
- A real send emits a "visitorNewMessage" websocket frame; the driver only reports sent=True when it
  SEES that frame carry our text, so SendResult is honest (no false positives). No CAPTCHA anywhere.
- Coverage caveat: only stores embedding Tidio via a direct code.tidio.co script tag initialise under
  automation; Shopify app-embed injections do not (-> no_tidio_api, retryable).
"""
from __future__ import annotations

from ..injector import SendResult
from ..widget_driver import VendorConfig, WidgetDriver

TIDIO = VendorConfig(
    vendor="tidio",
    widget_scope="#tidio-chat",
    ready_predicate="window.tidioChatApi && window.tidioChatApi.readyEventWasFired",
    ready_fallback_predicate="window.tidioChatApi",
    ready_timeout_ms=25000,
    not_ready_detail="no_tidio_api",
    open_js="window.tidioChatApi.open()",
    entry_labels=("Chat with us", "Send us a message", "New conversation",
                  "Start a conversation", "Start chat", "Get in touch", "Chat with Lyro"),
    email_strategy="prechat_then_api",
    email_api_js="window.tidioChatApi.setContactProperties({email: e})",
    confirm_strategy="wire_token",
    confirm_frame_marker="visitorNewMessage",
)


class TidioAdapter:
    vendor = "tidio"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        return WidgetDriver(TIDIO).send(domain, pitch, reply_email)
