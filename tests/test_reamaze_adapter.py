"""Re:amaze is a VendorConfig (REAMAZE) over the shared WidgetDriver (ADR-0007). These tests lock the
data the live probes established (research/crisp-reamaze-injection.md): DOM-drive, SDK window.Reamaze
(lazy, hence a long ready timeout), opened via Reamaze.popup(), conversation in an about:blank iframe
resolved by the composer marker (Tawk-style), no email gate (one-way model), confirmed by dom_echo.
"""
import inspect

from chat_outreach_engine.adapters.reamaze import REAMAZE, ReamazeAdapter
from chat_outreach_engine.widget_driver import VendorConfig, WidgetDriver


def test_adapter_delegates_under_the_reamaze_vendor():
    assert ReamazeAdapter.vendor == "reamaze"
    assert REAMAZE.vendor == "reamaze"


def test_is_dom_drive_config_not_a_class():
    assert isinstance(REAMAZE, VendorConfig)
    assert WidgetDriver(REAMAZE).config is REAMAZE


def test_config_waits_for_the_lazy_sdk_and_opens_via_popup():
    assert REAMAZE.ready_predicate == "window.Reamaze"
    assert REAMAZE.not_ready_detail == "no_reamaze_api"
    assert REAMAZE.ready_timeout_ms >= 30000      # SDK loads lazily; the gate must wait
    assert "popup" in REAMAZE.open_js and "catch" in REAMAZE.open_js


def test_config_resolves_the_about_blank_iframe_by_composer_marker():
    # the conversation renders in a same-origin about:blank iframe with no stable URL, so it is
    # resolved by content - the composer placeholder, which exists only inside that frame
    assert REAMAZE.widget_frame_marker == REAMAZE.composer_selector
    assert REAMAZE.widget_scope is None
    assert REAMAZE.widget_frame_url is None
    assert "textarea" in REAMAZE.composer_selector


def test_config_no_email_gate_and_dom_echo_confirm():
    assert REAMAZE.email_strategy == "none"
    assert REAMAZE.email_api_js is None
    assert REAMAZE.confirm_strategy == "dom_echo"


def test_send_exposes_dry_run_for_verify_to_composer():
    sig = inspect.signature(WidgetDriver.send)
    assert "dry_run" in sig.parameters and sig.parameters["dry_run"].default is False
