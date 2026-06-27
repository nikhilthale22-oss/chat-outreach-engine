"""Help Scout Beacon: a DOM-drive VendorConfig over WidgetDriver (ADR-0007). Its widget is a same-origin
about:blank iframe with a STABLE id #beacon-container, so it is resolved by that content marker (like
Tawk's about:srcdoc, not by URL). The "Ask" entry reaches a contact-form textarea. Locks the config; the
live send is a follow-up (the Ask form is fill+Send, not type+Enter)."""
from chat_outreach_engine.adapters.helpscout import HELPSCOUT, HelpScoutAdapter
from chat_outreach_engine.widget_driver import VendorConfig, WidgetDriver


def test_helpscout_is_a_dom_drive_config():
    assert isinstance(HELPSCOUT, VendorConfig)
    assert WidgetDriver(HELPSCOUT).config is HELPSCOUT
    assert HelpScoutAdapter.vendor == "helpscout" and HELPSCOUT.vendor == "helpscout"


def test_helpscout_resolves_beacon_iframe_by_stable_id():
    assert HELPSCOUT.widget_frame_marker == "#beacon-container"
    assert HELPSCOUT.widget_frame_url is None


def test_helpscout_opens_via_beacon_and_navigates_to_the_message_form():
    assert "Beacon('open')" in HELPSCOUT.open_js
    assert "navigate" in HELPSCOUT.open_js and "/ask/message/" in HELPSCOUT.open_js
    assert HELPSCOUT.entry_strategy == "by_text"
    assert HELPSCOUT.composer_selector == "textarea"
    assert HELPSCOUT.not_ready_detail == "no_beacon"
