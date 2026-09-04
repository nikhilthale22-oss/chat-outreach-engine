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
    # window.LiveChatWidget is a LOADER STUB that exists the instant the tracking snippet runs, so a
    # bare `window.LiveChatWidget` check passes even on a tracking-only / unlicensed install where the
    # chat widget never loads (verified live: teddybaldassarre + brackish ship cdn.livechatinc.com/
    # tracking.js only, and get('state') throws "You can't use getters before load" forever). Require
    # the widget to be actually LOADED - get('state') stops throwing once it is - so a dead install
    # fails fast+clean as no_livechat instead of grinding to a slow no_composer, and a live store is
    # only driven once its widget is really up.
    ready_predicate="(function(){try{return !!window.LiveChatWidget.get('state');}catch(e){return false;}})()",
    ready_fallback_predicate="(function(){try{return !!window.LiveChatWidget.get('state');}catch(e){return false;}})()",
    ready_timeout_ms=20000,
    not_ready_detail="no_livechat",
    open_js="window.LiveChatWidget.call('maximize')",
    entry_labels=("Start a conversation", "New conversation", "Chat with us", "Send a message"),
    # Offline, LiveChat shows a "Leave a message" FORM (name/email/subject/message + submit); the
    # contact_form path fills + submits it. When the store is ONLINE it is a live composer with no
    # form, so the driver falls back to the normal chat send + dom_echo.
    email_strategy="contact_form",
    email_api_js=None,
    # ONLINE, LiveChat is a websocket chat: the server acks a stored message with a start_chat
    # "response" frame carrying event_ids (the ids it assigned to our events). Delivered only on that
    # server receipt (ADR-0009), not a screen echo. OFFLINE it is a "Leave a message" contact_form,
    # which keeps the thank-you confirm in _submit_contact_form (no ack_response_re wired yet).
    confirm_strategy="wire_token",
    confirm_frame_marker=None,
    composer_selector="textarea",
    entry_strategy="by_text",
    widget_frame_url="livechatinc.com",
    # secure.livechatinc.com sends plain-JSON ws frames; a start_chat response with a non-empty
    # event_ids array = the server stored our message. Escape-tolerant so a SockJS-wrapped variant
    # still matches. An empty event_ids ([]) or an update_customer response does NOT match.
    ack_frame_re=r'event_ids\\?":\s*\[\s*\\?"',
)


class LiveChatAdapter:
    vendor = "livechat"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        return WidgetDriver(LIVECHAT).send(domain, pitch, reply_email)
