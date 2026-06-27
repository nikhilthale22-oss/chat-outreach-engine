"""API-send family: vendors that transmit a visitor message via a JS call (Intercom, Zendesk),
not by typing. ApiVendorConfig over ApiSendDriver (ADR-0007). These lock the config data; the live
send() and its dom_echo_any confirm are proven by a real run (NOT yet done - wired but unverified).
"""
from chat_outreach_engine.adapters.intercom import INTERCOM, IntercomAdapter
from chat_outreach_engine.api_send_driver import ApiSendDriver, ApiVendorConfig


def test_intercom_is_an_api_send_config():
    assert isinstance(INTERCOM, ApiVendorConfig)
    assert ApiSendDriver(INTERCOM).config is INTERCOM


def test_intercom_delegates_under_its_vendor():
    assert IntercomAdapter.vendor == "intercom" and INTERCOM.vendor == "intercom"


def test_intercom_sends_via_start_conversation():
    # startConversation transmits; showNewMessage only prefills (so we do NOT use it)
    assert "startConversation" in INTERCOM.send_js
    assert "showNewMessage" not in INTERCOM.send_js
    assert INTERCOM.open_js == "window.Intercom('show')"
    assert INTERCOM.confirm_strategy == "dom_echo_any"
    assert INTERCOM.not_ready_detail == "no_intercom"
