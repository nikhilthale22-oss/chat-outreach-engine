"""Tawk is a VendorConfig (TAWK) over the shared WidgetDriver (ADR-0007), the second DOM-drive
vendor and the first that lives in an iframe. These tests lock the Tawk-specific data the live
spike established (research/tawk-injection.md) - the frame marker, the maximize/ready/entry/composer
mechanics, the callback-flag confirm, and the no-email-gate default - and confirm the adapter
delegates under the same public surface. The live send() is proven by a real run.
"""
from chat_outreach_engine.adapters.tawk import TAWK, TawkAdapter
from chat_outreach_engine.widget_driver import VendorConfig, WidgetDriver


def test_adapter_delegates_under_the_tawk_vendor():
    # the vendor string must match the signature ("tawk.to") so the registry dispatches to it
    assert TawkAdapter.vendor == "tawk.to"
    assert TAWK.vendor == "tawk.to"


def test_is_dom_drive_config_not_a_class():
    assert isinstance(TAWK, VendorConfig)
    assert WidgetDriver(TAWK).config is TAWK


def test_config_resolves_the_widget_by_iframe_content_marker():
    # tawk renders in a same-origin iframe with no stable URL; resolve it by the panel root (present
    # on the Home screen of every widget variant, unlike the composer which some variants defer)
    assert TAWK.widget_frame_marker == ".tawk-chat-panel"
    assert TAWK.widget_scope is None          # the frame IS the scope


def test_config_opens_with_maximize_and_waits_on_tawk_api():
    assert TAWK.open_js == "window.Tawk_API.maximize()"
    assert "Tawk_API" in TAWK.ready_predicate
    assert TAWK.not_ready_detail == "no_tawk_api"


def test_config_drives_the_tawk_composer_by_text_entry():
    assert TAWK.composer_selector == "textarea.tawk-chatinput-editor"
    assert TAWK.entry_strategy == "by_text"
    assert "New Conversation" in TAWK.entry_labels


def test_config_confirms_via_dom_echo():
    # onChatMessageVisitor (registered post-load) did not fire on a real send; a sent message
    # instead lands in the rendered thread and clears the composer, which dom_echo checks.
    assert TAWK.confirm_strategy == "dom_echo"
    assert TAWK.confirm_setup_js is None


def test_config_uses_contact_form_for_offline_and_prechat_gate_for_custom_widgets():
    # ONLINE default widget: live composer, no email field -> falls through to the chat send.
    # OFFLINE: a leave-a-message form (Name/Email/Message + Submit) -> contact_form path files it.
    # CUSTOM widget: a Name/Email/Phone pre-chat gate -> prechat_form_gate fills+starts the chat.
    assert TAWK.email_strategy == "contact_form"
    assert TAWK.email_api_js is None
    assert TAWK.prechat_form_gate is True
