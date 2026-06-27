"""ChatraAdapter: the Adapter for Chatra (chatra.io) widgets.

A VendorConfig over the shared WidgetDriver (ADR-0007). Reverse-engineered live: Chatra exposes
window.Chatra (a command function) with openChat/expandWidget but NO message-transmit method, so it is
DOM-drive - type into the composer, press Enter. The widget renders in an iframe served from
chat.chatra.io, so the driver resolves the frame by that URL substring. The composer is a stable-classed
textarea.js-chat-textarea ("Message..."). Confirm via dom_echo. Even with the team offline, Chatra lets a
visitor type and queue a message, so the composer is reachable either way.
"""
from __future__ import annotations

from ..injector import SendResult
from ..widget_driver import VendorConfig, WidgetDriver

CHATRA = VendorConfig(
    vendor="chatra",
    widget_scope=None,
    ready_predicate="window.Chatra",
    ready_fallback_predicate="window.ChatraID",
    ready_timeout_ms=20000,
    not_ready_detail="no_chatra",
    open_js="window.Chatra('openChat', true)",
    entry_labels=("Start a conversation", "New conversation", "Chat with us", "Send a message"),
    email_strategy="none",
    email_api_js=None,
    confirm_strategy="dom_echo",
    confirm_frame_marker=None,
    composer_selector="textarea.js-chat-textarea, textarea[placeholder*='message' i]",
    entry_strategy="by_text",
    widget_frame_url="chatra.io",
)


class ChatraAdapter:
    vendor = "chatra"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        return WidgetDriver(CHATRA).send(domain, pitch, reply_email)
