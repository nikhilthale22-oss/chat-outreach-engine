"""Pure-helper tests for the Tidio adapter (the send() flow itself needs a live browser and is
exercised by real runs). _target_url is the seam that lets us point the adapter at an explicit
URL - a bare domain gets https, an explicit scheme is preserved (http test pages, http-only stores).
"""
from chat_outreach_engine.adapters.tidio import TidioAdapter


def test_target_url_prefixes_bare_domain_with_https():
    assert TidioAdapter._target_url("foo.com") == "https://foo.com"


def test_target_url_preserves_explicit_http_scheme():
    assert TidioAdapter._target_url("http://localhost:8088/") == "http://localhost:8088/"


def test_target_url_preserves_explicit_https_scheme():
    assert TidioAdapter._target_url("https://shop.example.com/page") == "https://shop.example.com/page"


# _pick_entry_label is the pure, browserless decision the v4/Lyro fix turns on: given the
# visible clickable texts inside the widget, which one do we click to reach the composer?
# v3 entry labels (substring, case-insensitive) win first and return the real on-screen text;
# the v4 Lyro Home screen is reached via 'Chat with Lyro', or as a last resort the bare 'Chat'
# bottom-nav tab matched EXACTLY (so we never grab 'chat' buried in an unrelated phrase).

def test_pick_entry_v3_direct_label():
    assert TidioAdapter._pick_entry_label(["Chat with us", "Send us a message"]) == "Chat with us"


def test_pick_entry_v3_substring_returns_onscreen_text():
    assert TidioAdapter._pick_entry_label(["Live Chat with us now"]) == "Live Chat with us now"


def test_pick_entry_v4_lyro_entry():
    assert TidioAdapter._pick_entry_label(["Chat with Lyro", "Powered by Tidio"]) == "Chat with Lyro"


def test_pick_entry_v4_nav_chat_tab_exact_last_resort():
    assert TidioAdapter._pick_entry_label(["Home", "Chat", "Help"]) == "Chat"


def test_pick_entry_none_when_no_entry_present():
    assert TidioAdapter._pick_entry_label(["Home", "Help", "FAQ"]) is None


def test_pick_entry_does_not_grab_chat_inside_a_phrase():
    # 'Chatbot FAQ' contains 'chat' but is not a v3 entry nor the exact nav tab -> no match.
    assert TidioAdapter._pick_entry_label(["Chatbot FAQ", "Home"]) is None


def test_pick_entry_tolerates_empty_and_falsy_texts():
    assert TidioAdapter._pick_entry_label([]) is None
    assert TidioAdapter._pick_entry_label([None, "", "   "]) is None


def test_pick_entry_v3_label_wins_over_bare_chat_nav():
    # When a real v3 entry AND a bare 'Chat' nav are both present, the entry wins (we must not
    # mis-click the nav tab when a proper start-conversation button exists).
    assert TidioAdapter._pick_entry_label(["Chat", "Start a conversation"]) == "Start a conversation"
