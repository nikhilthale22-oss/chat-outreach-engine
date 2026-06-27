"""Pure-helper tests for the shared WidgetDriver (the live send() needs a real browser and is
exercised by real runs / the Tidio parity run). These cover the vendor-agnostic decisions the
driver makes: which URL to load, how to scope a selector to the widget, what token to look for on
the wire, whether a send was confirmed, and which entry to click to reach the composer.
"""
from chat_outreach_engine.widget_driver import WidgetDriver


# _target_url: a bare domain gets https; an explicit scheme is preserved (http test pages,
# http-only stores).
def test_target_url_prefixes_bare_domain_with_https():
    assert WidgetDriver._target_url("foo.com") == "https://foo.com"


def test_target_url_preserves_explicit_http_scheme():
    assert WidgetDriver._target_url("http://localhost:8088/") == "http://localhost:8088/"


def test_target_url_preserves_explicit_https_scheme():
    assert WidgetDriver._target_url("https://shop.example.com/page") == "https://shop.example.com/page"


# _scoped: every comma-separated selector gets the widget scope prefixed so a query stays inside
# the widget; a None scope is page-level and passes through unchanged.
def test_scoped_prefixes_each_selector_with_scope():
    assert (WidgetDriver._scoped("#tidio-chat", "textarea, [contenteditable='true']")
            == "#tidio-chat textarea, #tidio-chat [contenteditable='true']")


def test_scoped_single_selector():
    assert WidgetDriver._scoped("#w", "button") == "#w button"


def test_scoped_none_is_page_level():
    assert WidgetDriver._scoped(None, "textarea, [contenteditable='true']") == "textarea, [contenteditable='true']"


# _pitch_token: a distinctive ASCII run to watch for on the wire - prefer 6+ chars, else the
# longest short run, else None when there is nothing alphanumeric.
def test_pitch_token_prefers_a_six_plus_char_run():
    assert WidgetDriver._pitch_token("Hi we build chatbots") == "chatbots"


def test_pitch_token_falls_back_to_longest_short_run():
    assert WidgetDriver._pitch_token("hi we go now") == "now"  # all <6 chars -> longest (ties: first)


def test_pitch_token_none_for_no_alphanumerics():
    assert WidgetDriver._pitch_token("!!! ... ???") is None


# _delivered: True iff a marker frame carries the token (raw or JSON-escaped); with no marker
# configured it can never confirm; with a marker but no token, a marker frame alone counts.
def test_delivered_true_when_marker_frame_carries_token():
    frames = ['{"event":"other"}', '{"event":"visitorNewMessage","text":"buy chatbots now"}']
    assert WidgetDriver._delivered(frames, "chatbots", "visitorNewMessage") is True


def test_delivered_false_when_marker_absent():
    frames = ['{"event":"typing","text":"chatbots"}']
    assert WidgetDriver._delivered(frames, "chatbots", "visitorNewMessage") is False


def test_delivered_false_when_no_marker_configured():
    frames = ['{"event":"visitorNewMessage","text":"chatbots"}']
    assert WidgetDriver._delivered(frames, "chatbots", None) is False


def test_delivered_falls_back_to_marker_presence_without_token():
    frames = ['{"event":"visitorNewMessage"}']
    assert WidgetDriver._delivered(frames, None, "visitorNewMessage") is True


# _pick_entry_label generic mechanics: vendor labels (case-insensitive substring) win first and
# return the real on-screen text; the exact bare 'Chat' nav tab is the last resort.
LABELS = ("Chat with us", "Start a conversation")


def test_pick_entry_substring_returns_onscreen_text():
    assert WidgetDriver._pick_entry_label(LABELS, ["Live Chat with us now"]) == "Live Chat with us now"


def test_pick_entry_exact_chat_nav_last_resort():
    assert WidgetDriver._pick_entry_label(LABELS, ["Home", "Chat", "Help"]) == "Chat"


def test_pick_entry_does_not_grab_chat_inside_a_phrase():
    assert WidgetDriver._pick_entry_label(LABELS, ["Chatbot FAQ", "Home"]) is None


def test_pick_entry_none_when_no_entry_present():
    assert WidgetDriver._pick_entry_label(LABELS, ["Home", "Help", "FAQ"]) is None


def test_pick_entry_tolerates_empty_and_falsy_texts():
    assert WidgetDriver._pick_entry_label(LABELS, []) is None
    assert WidgetDriver._pick_entry_label(LABELS, [None, "", "   "]) is None


def test_pick_entry_real_label_beats_bare_chat_nav():
    assert WidgetDriver._pick_entry_label(LABELS, ["Chat", "Start a conversation"]) == "Start a conversation"
