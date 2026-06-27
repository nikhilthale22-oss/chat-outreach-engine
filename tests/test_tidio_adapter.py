"""Tidio is now a VendorConfig (TIDIO) over the shared WidgetDriver (ADR-0007). These tests lock
the Tidio-specific data - the scope, readiness, the email/confirm strategies, and the entry labels
the v4/Lyro fix turns on - and confirm the adapter still delegates under the same public surface.
The generic driver mechanics live in test_widget_driver.py; the live send() is proven by real runs.
"""
from chat_outreach_engine.adapters.tidio import TIDIO, TidioAdapter
from chat_outreach_engine.widget_driver import WidgetDriver


def test_adapter_delegates_under_the_tidio_vendor():
    assert TidioAdapter.vendor == "tidio"
    assert TIDIO.vendor == "tidio"


def test_config_scopes_to_the_tidio_shadow_host():
    assert TIDIO.widget_scope == "#tidio-chat"


def test_config_confirms_on_the_wire_frame():
    assert TIDIO.confirm_strategy == "wire_token"
    assert TIDIO.confirm_frame_marker == "visitorNewMessage"


def test_config_reports_no_tidio_api_when_widget_never_comes_up():
    assert TIDIO.not_ready_detail == "no_tidio_api"


def test_config_attaches_email_via_set_contact_properties():
    assert TIDIO.email_strategy == "prechat_then_api"
    assert "setContactProperties" in TIDIO.email_api_js


# The v4/Lyro fix, locked: given the widget's visible texts, the right entry to click to reach
# the composer. v3 labels (substring, case-insensitive) return the real on-screen text; the v4
# Lyro Home screen is reached via 'Chat with Lyro' or, as a last resort, the exact 'Chat' nav tab.
def _pick(texts):
    return WidgetDriver._pick_entry_label(TIDIO.entry_labels, texts)


def test_config_carries_the_v4_lyro_entry_label():
    assert "Chat with Lyro" in TIDIO.entry_labels


def test_pick_entry_v3_direct_label():
    assert _pick(["Chat with us", "Send us a message"]) == "Chat with us"


def test_pick_entry_v3_substring_returns_onscreen_text():
    assert _pick(["Live Chat with us now"]) == "Live Chat with us now"


def test_pick_entry_v4_lyro_entry():
    assert _pick(["Chat with Lyro", "Powered by Tidio"]) == "Chat with Lyro"


def test_pick_entry_v4_nav_chat_tab_exact_last_resort():
    assert _pick(["Home", "Chat", "Help"]) == "Chat"


def test_pick_entry_none_when_no_entry_present():
    assert _pick(["Home", "Help", "FAQ"]) is None


def test_pick_entry_does_not_grab_chat_inside_a_phrase():
    assert _pick(["Chatbot FAQ", "Home"]) is None


def test_pick_entry_v3_label_wins_over_bare_chat_nav():
    assert _pick(["Chat", "Start a conversation"]) == "Start a conversation"
