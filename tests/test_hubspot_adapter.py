"""HubSpot Conversations: a DOM-drive VendorConfig over WidgetDriver (ADR-0007). Reverse-engineered
live on designerts.com (2026-07-19): the chat panel is a cross-origin app.hubspot.com/
conversations-visitor iframe, opened via HubSpotConversations.widget.load()+open(). These lock the
config the spike established, plus the detection->route->adapter wiring under the 'hubspot-chat' key."""
from chat_outreach_engine.adapters.hubspot import HUBSPOT, HubSpotAdapter
from chat_outreach_engine.detect import signatures
from chat_outreach_engine.injector import Detection
from chat_outreach_engine.route import registry
from chat_outreach_engine.route.router import route as route_detection
from chat_outreach_engine.send.headed import build_headed_adapters
from chat_outreach_engine.widget_driver import VendorConfig, WidgetDriver

signatures.compile_patterns()


def test_hubspot_is_a_dom_drive_config_keyed_hubspot_chat():
    assert isinstance(HUBSPOT, VendorConfig)
    assert HUBSPOT.vendor == "hubspot-chat" and HubSpotAdapter.vendor == "hubspot-chat"
    assert WidgetDriver(HUBSPOT).config is HUBSPOT


def test_config_matches_the_live_spike():
    # chat is only reachable once HubSpotConversations.widget exists (a tracking-only site lacks it)
    assert "HubSpotConversations" in HUBSPOT.ready_predicate and "widget" in HUBSPOT.ready_predicate
    assert HUBSPOT.not_ready_detail == "no_hubspot_api"
    # opened via the widget API, not a DOM click
    assert "widget.open()" in HUBSPOT.open_js and "widget.load()" in HUBSPOT.open_js
    # the panel is the cross-origin conversations-visitor iframe, resolved by URL substring
    assert HUBSPOT.widget_frame_url == "conversations-visitor"
    assert HUBSPOT.widget_frame_marker is None
    assert HUBSPOT.confirm_strategy == "dom_echo"
    # the composer is HubSpot's VizExExpandingInput, pinned by its stable data-test-id. It reflows
    # every frame, so send() focuses it rather than requiring an actionable click (proven live).
    assert HUBSPOT.composer_selector == "[data-test-id='widget-textarea']"
    # primary confirm is HubSpot's own server receipt: the visitor-message create POST (ADR-0009),
    # proven live on designerts.com - dom_echo alone false-negatives on the re-rendering widget.
    assert HUBSPOT.ack_response_re == r"livechat-public/v1/thread/visitor/create"


def test_hubspot_chat_detects_from_its_conversations_signal():
    # the HubSpotConversations api-call signal fingerprints the chat (the existing hubspot-chat rule).
    html = ('<script src="https://js.hs-scripts.com/6694002.js"></script>'
            '<script>window.HubSpotConversations = window.HubSpotConversations || {};</script>')
    hits = signatures.match_html(html)
    assert any(h["vendor"] == "hubspot-chat" for h in hits)


def test_hubspot_chat_routes_to_headed_and_has_an_adapter():
    d = Detection(has_widget=True, vendor="hubspot-chat", has_ai=False, kind="human",
                  category="helpdesk")
    decision = route_detection(d)
    assert decision.action == "send" and decision.method == registry.METHOD_HEADED
    assert "hubspot-chat" in build_headed_adapters()
