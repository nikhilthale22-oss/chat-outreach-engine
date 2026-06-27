"""LiveChatAdapter: the Adapter for LiveChat (livechat.com) widgets.

A VendorConfig over the shared WidgetDriver (ADR-0007). Reverse-engineered live: LiveChat exposes
window.LiveChatWidget with maximize/minimize/hide but NO message-transmit method (its full JS API is
control-only), so it is DOM-drive - type into the composer, press Enter. The widget renders in an
iframe served from secure.livechatinc.com, so the driver resolves the frame by that URL substring.
Confirm via dom_echo (our token appears in the rendered thread and the composer clears).

Probed open state: maximize() shows the conversation (or the offline "Leave a message" form), with a
composer textarea inside the livechatinc.com iframe. composer_selector is the bare textarea because
LiveChat's classes are build-hashed (not stable). email_strategy is "none" for now (online widgets have
no pre-chat email; the offline leave-a-message path is a follow-up).
"""
from __future__ import annotations

from ..injector import SendResult
from ..widget_driver import VendorConfig, WidgetDriver

LIVECHAT = VendorConfig(
    vendor="livechat",
    widget_scope=None,
    ready_predicate="window.LiveChatWidget",
    ready_fallback_predicate="window.__lc || window.LC_API",
    ready_timeout_ms=20000,
    not_ready_detail="no_livechat",
    open_js="window.LiveChatWidget.call('maximize')",
    entry_labels=("Start a conversation", "New conversation", "Chat with us", "Send a message"),
    email_strategy="none",
    email_api_js=None,
    confirm_strategy="dom_echo",
    confirm_frame_marker=None,
    composer_selector="textarea",
    entry_strategy="by_text",
    widget_frame_url="livechatinc.com",
)


class LiveChatAdapter:
    vendor = "livechat"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        return WidgetDriver(LIVECHAT).send(domain, pitch, reply_email)
