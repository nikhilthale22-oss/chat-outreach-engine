"""Shopify Inbox is its OWN Adapter class (ADR-0007 "different control flow -> its own class"): an
open-shadow-DOM widget whose send flow is type -> Send -> contact form -> Start chat -> dom_echo. These
tests lock the honesty seam (_verdict: what counts as delivered vs blocked) and the public surface. The
live flow is proven by a real delivered message (research/shopify-inbox-injection.md).
"""
import inspect

from chat_outreach_engine.adapters.shopify_inbox import ShopifyInboxAdapter
from chat_outreach_engine.injector import SendResult


def test_vendor_string_matches_the_dispatch_key():
    assert ShopifyInboxAdapter.vendor == "shopify-inbox"


def test_send_exposes_dry_run_for_verify_to_composer():
    sig = inspect.signature(ShopifyInboxAdapter.send)
    assert "dry_run" in sig.parameters and sig.parameters["dry_run"].default is False


def test_verdict_delivered_only_when_pitch_in_thread():
    r = ShopifyInboxAdapter._verdict({"pitch_in_thread": True}, submitted=True)
    assert r == SendResult(True, "delivered")


def test_verdict_visible_challenge_is_not_delivered_even_if_pitch_present():
    # passive hCaptcha flagged the session: a visible challenge means we were blocked, never claim a send
    r = ShopifyInboxAdapter._verdict({"pitch_in_thread": True, "challenge_visible": True}, submitted=True)
    assert r.sent is False and r.detail == "captcha_challenge"


def test_verdict_submitted_but_unconfirmed_is_terminal_to_prevent_double_send():
    # Start chat was clicked (message committed) but no confirmation -> never retry, or we could double-send
    r = ShopifyInboxAdapter._verdict({"pitch_in_thread": False, "form_present": False}, submitted=True)
    assert r.sent is False and r.detail == "submitted_unconfirmed"


def test_verdict_lingering_form_without_submit_is_held():
    r = ShopifyInboxAdapter._verdict({"pitch_in_thread": False, "form_present": True}, submitted=False)
    assert r.sent is False and r.detail == "form_blocked"


def test_verdict_no_signal_and_no_submit_is_retryable_unconfirmed():
    # nothing was committed, so this is a normal retryable miss (not a double-send risk)
    r = ShopifyInboxAdapter._verdict({"pitch_in_thread": False, "form_present": False}, submitted=False)
    assert r.sent is False and r.detail == "no_delivery_confirmation"


def test_submitted_unconfirmed_is_terminal_in_batch():
    # the batch must treat a committed-but-unconfirmed send as terminal (Dead), never re-pitch it
    from chat_outreach_engine.batch import TERMINAL_SEND_DETAILS
    assert {"submitted_unconfirmed", "form_blocked", "captcha_challenge"} <= TERMINAL_SEND_DETAILS
