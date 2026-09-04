"""HubSpotAdapter: the Adapter for HubSpot Conversations (chat) widgets.

A VendorConfig over the shared WidgetDriver (ADR-0007). Reverse-engineered live (spike on
designerts.com, 2026-07-19): window.HubSpotConversations.widget controls the chat. widget.load()
then widget.open() surfaces the panel. The chat renders in a CROSS-ORIGIN iframe served from
app.hubspot.com/conversations-visitor/<portalId>/threads/... (id="hubspot-conversations-iframe",
data-test-id="chat-widget-iframe"), so the driver resolves the widget frame by that URL substring
(widget_frame_url="conversations-visitor") and drives the composer inside it via Playwright frame
access (page JS cannot cross into it). Confirm via dom_echo.

- HubSpotConversations exposes NO visitor message-transmit method (widget API is load/open/close/
  refresh/status/remove only), so it is DOM-drive: open, type into the composer, Enter.
- Coverage caveat (important): the STATIC tag that appears on a HubSpot site is js.hs-scripts.com,
  which is HubSpot TRACKING and loads on every HubSpot-tracked site whether or not chat is enabled
  (verified: bravadodesigns.com ships hs-scripts but HubSpotConversations is undefined). The chat
  bundle (js.usemessages.com) is injected at RUNTIME, so static detection under-counts chat-enabled
  stores; the honest signal is the runtime HubSpotConversations global. See signatures.py.

STATUS: adapter built + open/iframe verified live. Composer reverse-engineered on designerts.com
(2026-07-19): data-test-id="widget-textarea", a VizExExpandingInput contenteditable. It is driven by
focus()+type (its per-frame reflow defeats Playwright's .click() stability check - proven live: click
times out, focus()+type and fill() both land text). The real-merchant delivery is the proof milestone.
"""
from __future__ import annotations

from ..injector import SendResult
from ..widget_driver import VendorConfig, WidgetDriver

HUBSPOT = VendorConfig(
    vendor="hubspot-chat",
    widget_scope=None,
    # window.HubSpotConversations.widget is present only once the CHAT bundle has loaded (a
    # tracking-only HubSpot site never defines it -> no_hubspot_api, a clean skip).
    ready_predicate="window.HubSpotConversations && window.HubSpotConversations.widget",
    ready_fallback_predicate="window.HubSpotConversations",
    ready_timeout_ms=20000,
    not_ready_detail="no_hubspot_api",
    # load() forces the widget bundle in, open() surfaces the panel; both guarded by the driver.
    open_js="window.HubSpotConversations.widget.load(); window.HubSpotConversations.widget.open()",
    entry_labels=("Send us a message", "Start a conversation", "Send a message",
                  "Message us", "Chat with us", "Start chat"),
    email_strategy="none",
    email_api_js=None,
    # Primary confirm is HubSpot's OWN server receipt (ADR-0009): the visitor message is created by a
    # POST 200 to app.hubspot.com/api/livechat-public/v1/thread/visitor/create whose body echoes our
    # richText back (verified live on designerts.com, 2026-07-19). All our sends are first-contact, so
    # that endpoint is always the receipt. dom_echo stays as a fallback - HubSpot's widget re-renders
    # before a surface-text check can see the sent bubble, so dom_echo alone false-negatives.
    ack_response_re=r"livechat-public/v1/thread/visitor/create",
    confirm_strategy="dom_echo",
    confirm_frame_marker=None,
    entry_strategy="by_text",
    # The chat panel is a cross-origin app.hubspot.com/conversations-visitor iframe with no stable id
    # we can rely on across skins; the URL substring is the durable marker.
    widget_frame_url="conversations-visitor",
    # The composer is HubSpot's VizExExpandingInput: a contenteditable div carrying a stable
    # data-test-id. Pin it (the generic textarea/contenteditable default also matches, but this is
    # unambiguous). It is an auto-expanding input that reflows every frame, so Playwright's .click()
    # stability check never settles - the driver focuses it via focus() instead (see widget_driver
    # send()), which is why send() does not depend on an actionable click here.
    composer_selector="[data-test-id='widget-textarea']",
)


class HubSpotAdapter:
    vendor = "hubspot-chat"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        return WidgetDriver(HUBSPOT).send(domain, pitch, reply_email)
