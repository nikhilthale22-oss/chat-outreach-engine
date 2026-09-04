"""LiveChat and Chatra: two more DOM-drive vendors as VendorConfigs over WidgetDriver (ADR-0007).
Both render in an iframe with a stable URL (livechatinc.com / chatra.io), so they are resolved by
widget_frame_url rather than an in-frame content marker (Tawk's about:srcdoc case). These lock the
config data the live probe established; the live send() is proven by real runs.
"""
from chat_outreach_engine.adapters.chatra import CHATRA, ChatraAdapter
from chat_outreach_engine.adapters.livechat import LIVECHAT, LiveChatAdapter
from chat_outreach_engine.widget_driver import VendorConfig, WidgetDriver


def test_both_are_dom_drive_configs_not_classes():
    assert isinstance(LIVECHAT, VendorConfig) and isinstance(CHATRA, VendorConfig)
    assert WidgetDriver(LIVECHAT).config is LIVECHAT
    assert WidgetDriver(CHATRA).config is CHATRA


def test_adapters_delegate_under_their_signature_vendor():
    assert LiveChatAdapter.vendor == "livechat" and LIVECHAT.vendor == "livechat"
    assert ChatraAdapter.vendor == "chatra" and CHATRA.vendor == "chatra"


def test_livechat_resolves_frame_by_url_and_opens_via_api():
    assert LIVECHAT.widget_frame_url == "livechatinc.com"
    assert LIVECHAT.widget_frame_marker is None
    assert "LiveChatWidget" in LIVECHAT.ready_predicate
    assert LIVECHAT.open_js == "window.LiveChatWidget.call('maximize')"
    # ONLINE LiveChat now confirms on the server's own receipt (a start_chat response with event_ids),
    # not a screen echo (ADR-0009). The offline leave-a-message form path is unchanged.
    assert LIVECHAT.confirm_strategy == "wire_token" and LIVECHAT.ack_frame_re


def test_chatra_resolves_frame_by_url_and_opens_via_api():
    assert CHATRA.widget_frame_url == "chatra.io"
    assert CHATRA.widget_frame_marker is None
    assert "Chatra" in CHATRA.ready_predicate
    assert "openChat" in CHATRA.open_js
    assert "js-chat-textarea" in CHATRA.composer_selector
    assert CHATRA.confirm_strategy == "dom_echo"


def test_livechat_uses_the_contact_form_gate():
    # Offline, LiveChat is a leave-a-message form; the contact_form path fills + submits it (an
    # online store has no form and falls back to the chat send + dom_echo).
    assert LIVECHAT.email_strategy == "contact_form"


def test_chatra_uses_the_composer_intro_gate():
    # Chatra holds a message behind a name/email intro typed into the composer; composer_intro
    # fills it so the held message flushes.
    assert CHATRA.email_strategy == "composer_intro"
