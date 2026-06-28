"""Zendesk is a VendorConfig (ZENDESK) over the shared WidgetDriver (ADR-0007). These tests lock the
Zendesk-specific data the live probes established (research/zendesk-injection.md): it is DOM-drive
(not api-send), targets the modern "messaging" widget whose conversation panel is a srcdoc/blank
iframe resolved by the composer marker, opens via every zE open verb, and confirms via dom_echo. The
verify-to-composer path is proven by a real run (5/5 messaging stores via dry_run).
"""
import inspect

from chat_outreach_engine.adapters.zendesk import ZENDESK, ZendeskAdapter
from chat_outreach_engine.widget_driver import VendorConfig, WidgetDriver


def test_adapter_delegates_under_the_zendesk_vendor():
    # the vendor string must match the signature ("zendesk") so the registry dispatches to it
    assert ZendeskAdapter.vendor == "zendesk"
    assert ZENDESK.vendor == "zendesk"


def test_is_dom_drive_config_not_a_class():
    # the deferral assumed api-send (async newConversation->sendMessage); the probe showed a real
    # composer, so Zendesk is DOM-drive like Tawk/LiveChat, not an ApiSendDriver vendor
    assert isinstance(ZENDESK, VendorConfig)
    assert WidgetDriver(ZENDESK).config is ZENDESK


def test_config_resolves_the_messaging_panel_by_composer_marker():
    # the messaging panel is a srcdoc/blank iframe titled "Messaging window" with no stable URL/id,
    # so it is resolved by content - the composer placeholder, which is in that frame and nowhere else
    assert ZENDESK.widget_frame_marker == "textarea[placeholder='Type a message' i]"
    assert ZENDESK.widget_scope is None          # the resolved frame IS the scope
    assert ZENDESK.widget_frame_url is None


def test_config_opens_with_every_ze_verb_each_guarded():
    # fire messenger/webWidget/activate, each in its own try/catch, so a throw on the verbs that do
    # not apply to this store's family does not block the one that does
    assert "messenger" in ZENDESK.open_js and "webWidget" in ZENDESK.open_js
    assert "activate" in ZENDESK.open_js
    assert ZENDESK.open_js.count("catch") >= 3
    assert ZENDESK.ready_predicate == "window.zE"
    assert ZENDESK.not_ready_detail == "no_zendesk_api"


def test_config_drives_the_messaging_composer():
    assert ZENDESK.composer_selector == "textarea[placeholder='Type a message' i]"


def test_config_confirms_via_dom_echo():
    # zE has no one-call send and no reliable sent-callback, so confirm by the sent message echoing
    # into the thread and clearing the composer (same as Tawk)
    assert ZENDESK.confirm_strategy == "dom_echo"


def test_config_has_no_prechat_email_gate_on_messaging():
    # the messaging composer takes a message immediately; email is collected mid-conversation if at all
    assert ZENDESK.email_strategy == "none"
    assert ZENDESK.email_api_js is None


def test_send_exposes_dry_run_for_verify_to_composer():
    # verify-to-composer (reach the composer, transmit nothing) is the unattended-safe proof path
    sig = inspect.signature(WidgetDriver.send)
    assert "dry_run" in sig.parameters
    assert sig.parameters["dry_run"].default is False
