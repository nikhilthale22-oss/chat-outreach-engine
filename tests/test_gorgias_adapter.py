"""Gorgias is an ApiVendorConfig (GORGIAS) over the shared ApiSendDriver (ADR-0007) - it transmits
via window.GorgiasChat.sendMessage and confirms by dom_echo_any, NOT the old optimistic "pitch_sent".
These tests lock that shape (no live browser).
"""
from chat_outreach_engine.adapters.gorgias import GORGIAS, GorgiasAdapter
from chat_outreach_engine.api_send_driver import ApiSendDriver, ApiVendorConfig


def test_adapter_under_the_gorgias_vendor():
    assert GorgiasAdapter.vendor == "gorgias"
    assert GORGIAS.vendor == "gorgias"


def test_is_api_send_config_not_a_hand_written_send():
    assert isinstance(GORGIAS, ApiVendorConfig)
    assert ApiSendDriver(GORGIAS).config is GORGIAS


def test_ready_targets_the_chat_widget_not_the_helpdesk_bridge():
    # the chat widget exposes window.GorgiasChat; helpdesk-only stores expose only GorgiasBridge and
    # must fail readiness, so the predicate is GorgiasChat and the detail names the chat explicitly
    assert GORGIAS.ready_predicate == "window.GorgiasChat"
    assert GORGIAS.not_ready_detail == "no_gorgias_chat"


def test_send_captures_email_then_sends_via_sendmessage():
    assert "captureUserEmail" in GORGIAS.send_js
    assert "sendMessage(m)" in GORGIAS.send_js
    # email capture must precede the send so the gate is satisfied before transmit
    assert GORGIAS.send_js.index("captureUserEmail") < GORGIAS.send_js.index("sendMessage")


def test_open_boots_and_opens_the_chat():
    assert "init" in GORGIAS.open_js
    assert "open" in GORGIAS.open_js


def test_confirm_is_dom_echo_any():
    # honest confirm: the Pitch token must render in the Messenger, no optimistic pitch_sent
    assert GORGIAS.confirm_strategy == "dom_echo_any"
