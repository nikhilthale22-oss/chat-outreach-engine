"""Olark is a VendorConfig (OLARK) over the shared WidgetDriver (ADR-0007). These tests lock the
Olark-specific data live probes established (research/widget-vendor-spike.md): DOM-drive (not
api-send), SDK window.olark, opened via olark('api.box.expand'), composer rendered in the PAGE DOM
(a generated `olark-custom-element-` <textarea>, not a UI iframe), no email gate (one-way model),
confirmed by dom_echo. Verify-to-composer proven via dry_run on live Olark stores.
"""
import inspect

from chat_outreach_engine.adapters.olark import OLARK, OlarkAdapter
from chat_outreach_engine.widget_driver import VendorConfig, WidgetDriver


def test_adapter_delegates_under_the_olark_vendor():
    assert OlarkAdapter.vendor == "olark"
    assert OLARK.vendor == "olark"


def test_is_dom_drive_config_not_a_class():
    assert isinstance(OLARK, VendorConfig)
    assert WidgetDriver(OLARK).config is OLARK


def test_config_uses_the_olark_sdk_and_opens_via_box_expand():
    assert OLARK.ready_predicate == "window.olark"
    assert OLARK.not_ready_detail == "no_olark_api"
    assert "api.box.expand" in OLARK.open_js
    assert OLARK.open_js.count("catch") >= 2     # box.expand + box.show, each guarded


def test_config_drives_a_page_level_composer_not_an_iframe():
    # Olark injects its chatbox into the host page DOM, so there is no widget iframe to resolve
    assert OLARK.widget_scope is None
    assert OLARK.widget_frame_marker is None
    assert OLARK.widget_frame_url is None
    assert "textarea" in OLARK.composer_selector


def test_composer_selector_targets_the_message_textarea_only():
    # the `olark-custom-element-` id prefix is shared by the inline name/email INPUTs; scoping the
    # selector to <textarea> keeps it on the message box and off those optional fields
    assert OLARK.composer_selector.startswith("textarea")
    assert "olark-custom-element" in OLARK.composer_selector


def test_config_no_email_gate_and_dom_echo_confirm():
    # one-way model: deliver only, no inbound reply path needed
    assert OLARK.email_strategy == "none"
    assert OLARK.email_api_js is None
    assert OLARK.confirm_strategy == "dom_echo"


def test_send_exposes_dry_run_for_verify_to_composer():
    sig = inspect.signature(WidgetDriver.send)
    assert "dry_run" in sig.parameters and sig.parameters["dry_run"].default is False
