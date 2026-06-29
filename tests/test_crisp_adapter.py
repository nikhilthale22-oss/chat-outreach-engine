"""Crisp is a VendorConfig (CRISP) over the shared WidgetDriver (ADR-0007). These tests lock the
Crisp-specific data the live probes established (research/crisp-reamaze-injection.md): DOM-drive
(not api-send), SDK window.$crisp, opened via $crisp chat:open, composer rendered in the PAGE DOM
(not an iframe), no email gate (one-way model), confirmed by dom_echo. Verify-to-composer proven via
dry_run on live Crisp stores.
"""
import inspect

from chat_outreach_engine.adapters.crisp import CRISP, CrispAdapter
from chat_outreach_engine.widget_driver import VendorConfig, WidgetDriver


def test_adapter_delegates_under_the_crisp_vendor():
    assert CrispAdapter.vendor == "crisp"
    assert CRISP.vendor == "crisp"


def test_is_dom_drive_config_not_a_class():
    assert isinstance(CRISP, VendorConfig)
    assert WidgetDriver(CRISP).config is CRISP


def test_config_uses_the_crisp_sdk_and_opens_via_chat_open():
    assert CRISP.ready_predicate == "window.$crisp"
    assert CRISP.not_ready_detail == "no_crisp_api"
    assert "chat:open" in CRISP.open_js
    assert CRISP.open_js.count("catch") >= 2     # chat:show + chat:open, each guarded


def test_config_drives_a_page_level_composer_not_an_iframe():
    # Crisp injects its chatbox into the host page DOM, so there is no widget iframe to resolve
    assert CRISP.widget_scope is None
    assert CRISP.widget_frame_marker is None
    assert CRISP.widget_frame_url is None
    assert "textarea" in CRISP.composer_selector


def test_config_no_email_gate_and_dom_echo_confirm():
    # one-way model: deliver only, no inbound reply path needed
    assert CRISP.email_strategy == "none"
    assert CRISP.email_api_js is None
    assert CRISP.confirm_strategy == "dom_echo"


def test_send_exposes_dry_run_for_verify_to_composer():
    sig = inspect.signature(WidgetDriver.send)
    assert "dry_run" in sig.parameters and sig.parameters["dry_run"].default is False
