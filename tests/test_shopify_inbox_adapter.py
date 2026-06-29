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


# ----- confirm robustness: the rendered thread text rarely matches the source Pitch byte-for-byte -----
# (this is what turned ~12 committed sends into false submitted_unconfirmed at scale: the thread's
#  textContent concatenates DOM nodes without spaces and carries newlines/tabs, so a space-joined
#  signature substring-check missed delivered messages. The match must be whitespace-insensitive.)

def test_thread_has_pitch_confirms_exact_render():
    thread = "Chat You sent: Hey, saw you don't have an AI chatbot on your site. Built one"
    assert ShopifyInboxAdapter._thread_has_pitch(thread, "Hey, saw you don't have an AI chatbot on your site.") is True


def test_thread_has_pitch_tolerates_rendering_whitespace_variance():
    # node-split / wrapped render: words joined, newlines and tabs where the Pitch had single spaces
    pitch = "Hey, saw you don't have an AI chatbot on your site."
    thread = "Hey,saw  you\ndon't\thave an AI\nchatbot on your\tsite."
    assert ShopifyInboxAdapter._thread_has_pitch(thread, pitch) is True


def test_thread_has_pitch_false_when_pitch_absent():
    assert ShopifyInboxAdapter._thread_has_pitch("Hi there, how can we help you today?",
                                                 "Hey, saw you don't have an AI chatbot on your site.") is False


def test_thread_has_pitch_false_on_common_word_overlap_only():
    # the widget's own canned text shares the word "interested" with PITCH_A; that must NOT confirm a send
    from chat_outreach_engine.pitches import PITCH_A
    assert ShopifyInboxAdapter._thread_has_pitch("Thanks! Are you interested in a quick demo?", PITCH_A) is False


def test_thread_has_pitch_false_on_empty_pitch():
    # never claim delivery off an empty Pitch (a stripped empty key would substring-match anything)
    assert ShopifyInboxAdapter._thread_has_pitch("any thread text at all", "") is False


# ----- form-fill robustness: the "Before we get started" form varies by store/locale (form_blocked) ---
# The fill must assign by field TYPE/keyword + POSITION, not English placeholders, or non-English /
# variant forms never submit. The planner returns a value per field (parallel list); None = leave blank.

def test_form_plan_standard_english():
    fields = [{"type": "text", "placeholder": "First Name", "name": "first_name"},
              {"type": "text", "placeholder": "Last Name", "name": "last_name"},
              {"type": "email", "placeholder": "Email", "name": "email"}]
    assert ShopifyInboxAdapter._plan_form_values(fields, "Nikhil", "Thale", "me@x.com") == \
        ["Nikhil", "Thale", "me@x.com"]


def test_form_plan_email_detected_by_keyword_when_type_is_text():
    # some stores render the email input as type=text; detect it by placeholder/name keyword, not type
    fields = [{"type": "text", "placeholder": "First Name", "name": "first"},
              {"type": "text", "placeholder": "Last Name", "name": "last"},
              {"type": "text", "placeholder": "Email", "name": "email"}]
    assert ShopifyInboxAdapter._plan_form_values(fields, "Nikhil", "Thale", "me@x.com") == \
        ["Nikhil", "Thale", "me@x.com"]


def test_form_plan_non_english_placeholders_fill_positionally():
    # French store: names have no English placeholder; email caught by type -> names fill by position
    fields = [{"type": "text", "placeholder": "Prenom", "name": ""},
              {"type": "text", "placeholder": "Nom", "name": ""},
              {"type": "email", "placeholder": "Courriel", "name": ""}]
    assert ShopifyInboxAdapter._plan_form_values(fields, "Nikhil", "Thale", "me@x.com") == \
        ["Nikhil", "Thale", "me@x.com"]


def test_form_plan_single_name_field_gets_full_name():
    fields = [{"type": "text", "placeholder": "Your name", "name": "name"},
              {"type": "email", "placeholder": "Email", "name": "email"}]
    assert ShopifyInboxAdapter._plan_form_values(fields, "Nikhil", "Thale", "me@x.com") == \
        ["Nikhil Thale", "me@x.com"]


def test_form_plan_email_only():
    fields = [{"type": "email", "placeholder": "Email", "name": "email"}]
    assert ShopifyInboxAdapter._plan_form_values(fields, "Nikhil", "Thale", "me@x.com") == ["me@x.com"]
