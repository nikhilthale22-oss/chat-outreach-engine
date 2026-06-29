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


def test_verdict_clicked_start_chat_is_always_terminal_even_if_form_lingers():
    # SAFETY INVARIANT (double-send): once Start chat is clicked the message may be committed, so the
    # send is NEVER retryable - regardless of whether the form snapshot still reads present (a lingering
    # / post-delivery input could false-positive form_present). `submitted` wins over form_present.
    gone = ShopifyInboxAdapter._verdict({"pitch_in_thread": False, "form_present": False}, submitted=True)
    lingering = ShopifyInboxAdapter._verdict({"pitch_in_thread": False, "form_present": True}, submitted=True)
    assert gone == SendResult(False, "submitted_unconfirmed")
    assert lingering == SendResult(False, "submitted_unconfirmed")


def test_verdict_form_gone_not_clicked_no_render_is_terminal_formless_directpost():
    # We ALWAYS clicked Send before the verdict. If the form is gone and we never clicked Start chat and
    # nothing rendered, a form-less / returning-visitor store may have posted directly on Send -> treat as
    # committed-unconfirmable (TERMINAL), never a clean retryable miss (that was the form-less double-send).
    r = ShopifyInboxAdapter._verdict({"pitch_in_thread": False, "form_present": False}, submitted=False)
    assert r.sent is False and r.detail == "submitted_unconfirmed"


def test_verdict_lingering_form_without_submit_is_held():
    r = ShopifyInboxAdapter._verdict({"pitch_in_thread": False, "form_present": True}, submitted=False)
    assert r.sent is False and r.detail == "form_blocked"


def test_error_after_send_clicked_is_terminal_not_retryable():
    # SAFETY: once Send is clicked the message MAY have posted (form-less stores post on Send). ANY later
    # exception (TargetClosedError / proxy drop / crash, common at scale) must yield a TERMINAL detail,
    # never a raw retryable error string - or the next run re-pitches a possibly-delivered merchant.
    assert ShopifyInboxAdapter._error_detail("TargetClosedError: page closed", committed=True) == "submitted_unconfirmed"


def test_error_before_send_stays_retryable():
    # failed BEFORE clicking Send -> nothing posted -> keep the raw error string (retryable)
    assert ShopifyInboxAdapter._error_detail("TimeoutError: goto", committed=False) == "TimeoutError: goto"


def test_only_genuinely_committed_details_are_terminal_in_batch():
    # submitted_unconfirmed (form GONE + clicked = committed) and a visible captcha stay terminal so a
    # retry can never double-send. form_blocked (form STILL UP = nothing posted) is now RETRYABLE - it
    # must NOT be terminal, or we permanently burn stores the silent-reject merely failed on once.
    from chat_outreach_engine.batch import TERMINAL_SEND_DETAILS
    assert {"submitted_unconfirmed", "captcha_challenge"} <= TERMINAL_SEND_DETAILS
    assert "form_blocked" not in TERMINAL_SEND_DETAILS


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


def test_thread_has_pitch_tolerates_smart_quotes_and_html_entities():
    # chat widgets routinely smart-quote (don't -> don[U+2019]t); the source Pitch has an ASCII apostrophe.
    # The match folds ALL non-alphanumerics, so a genuinely delivered message still confirms - otherwise a
    # smart-quoting store reads delivered messages as not-delivered (a confirm false-negative).
    from chat_outreach_engine.pitches import PITCH_A
    smart = "You sent: " + PITCH_A.replace("'", "’")
    assert ShopifyInboxAdapter._thread_has_pitch(smart, PITCH_A) is True


def test_match_key_differs_between_pitch_variants():
    # PITCH_A and PITCH_B share an opening; the key must reach far enough to differ, or a variant-B send
    # could read 'delivered' off a variant-A message (masking a real double-send in a shared thread).
    from chat_outreach_engine.pitches import PITCH_A, PITCH_B
    assert ShopifyInboxAdapter._match_key(PITCH_A) != ShopifyInboxAdapter._match_key(PITCH_B)


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
