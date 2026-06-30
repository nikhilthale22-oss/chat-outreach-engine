"""Zoho SalesIQ is a VendorConfig (ZOHO_SALESIQ) over the shared WidgetDriver (ADR-0007). These
tests lock the data live probes established (research/widget-vendor-spike.md): DOM-drive (not
api-send), SDK window.$zoho.salesiq, opened via the float-window / chat.start verbs, composer
(<textarea id="msgarea">) rendered in an about:blank iframe resolved by in-frame content marker,
no email gate (one-way model), confirmed by dom_echo.
"""
import inspect

from chat_outreach_engine.adapters.zoho_salesiq import ZOHO_SALESIQ, ZohoSalesIQAdapter
from chat_outreach_engine.widget_driver import VendorConfig, WidgetDriver


def test_adapter_delegates_under_the_zoho_vendor():
    assert ZohoSalesIQAdapter.vendor == "zoho-salesiq"
    assert ZOHO_SALESIQ.vendor == "zoho-salesiq"


def test_is_dom_drive_config_not_a_class():
    assert isinstance(ZOHO_SALESIQ, VendorConfig)
    assert WidgetDriver(ZOHO_SALESIQ).config is ZOHO_SALESIQ


def test_config_uses_the_zoho_sdk_and_opens_the_chat():
    assert ZOHO_SALESIQ.ready_predicate == "window.$zoho && window.$zoho.salesiq"
    assert ZOHO_SALESIQ.not_ready_detail == "no_zoho_api"
    assert "salesiq" in ZOHO_SALESIQ.open_js
    assert "chat.start" in ZOHO_SALESIQ.open_js


def test_config_resolves_an_about_blank_frame_by_content_marker():
    # Zoho's chat UI is an iframe with no stable URL, so the driver resolves it by an in-frame marker
    assert ZOHO_SALESIQ.widget_frame_url is None
    assert ZOHO_SALESIQ.widget_frame_marker is not None
    assert "textarea" in ZOHO_SALESIQ.widget_frame_marker
    # the marker is the composer itself, so the resolved frame is guaranteed to hold the message box
    assert ZOHO_SALESIQ.widget_frame_marker == ZOHO_SALESIQ.composer_selector


def test_composer_targets_the_message_textarea():
    assert "msgarea" in ZOHO_SALESIQ.composer_selector
    assert "textarea" in ZOHO_SALESIQ.composer_selector


def test_config_no_email_gate_and_dom_echo_confirm():
    assert ZOHO_SALESIQ.email_strategy == "none"
    assert ZOHO_SALESIQ.email_api_js is None
    assert ZOHO_SALESIQ.confirm_strategy == "dom_echo"


def test_send_exposes_dry_run_for_verify_to_composer():
    sig = inspect.signature(WidgetDriver.send)
    assert "dry_run" in sig.parameters and sig.parameters["dry_run"].default is False
