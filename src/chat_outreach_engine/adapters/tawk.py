"""TawkAdapter: the Adapter for tawk.to live-chat widgets.

Tawk is the second DOM-drive vendor, so it is a VendorConfig (TAWK) over the shared WidgetDriver,
not hand-written flow (ADR-0007). Reverse-engineered live against real stores (research/tawk-injection.md):

- Tawk_API has NO message-send method (the full surface is open/identify/status + read-only event
  callbacks), so a visitor message must be DOM-driven: open the widget, type into the composer, Enter.
- The v4 widget renders its chat panel in a SAME-ORIGIN about:srcdoc iframe with no stable URL or name.
  The driver resolves that frame by content: the frame containing `.tawk-chatinput-editor`.
- Flow: maximize() to open -> the Home screen shows a "New Conversation" entry -> click it -> the
  composer `textarea.tawk-chatinput-editor` (the visible one of two) -> type -> Enter ("Type here and
  press enter.." literally tells the visitor to). Confirm via the onChatMessageVisitor callback, which
  fires after the visitor's message is sent (installed as confirm_setup_js).
- Email gate: the default widget has none (composer is immediate). email_strategy="none". Leaving a
  reply address for tawk is a separate, unproven reply-capture concern (see research/tawk-injection.md).
- Coverage caveat: only stores embedding a direct embed.tawk.to/<pid>/<wid> loader pass the live gate;
  app-embed / deferred-injection stores have no static tag (same static-gap as Tidio).
"""
from __future__ import annotations

from ..injector import SendResult
from ..widget_driver import VendorConfig, WidgetDriver

TAWK = VendorConfig(
    vendor="tawk.to",
    widget_scope=None,                       # the resolved iframe IS the scope
    ready_predicate="window.Tawk_API && window.Tawk_API.maximize",
    ready_fallback_predicate="window.Tawk_API",
    ready_timeout_ms=20000,
    not_ready_detail="no_tawk_api",
    open_js="window.Tawk_API.maximize()",
    entry_labels=("New Conversation", "Start a conversation", "Send us a message",
                  "Chat with us", "Start chat"),
    email_strategy="none",
    email_api_js=None,
    confirm_strategy="callback_flag",
    confirm_frame_marker=None,
    composer_selector="textarea.tawk-chatinput-editor",
    entry_selector="button, [role='button']",
    entry_strategy="by_text",
    # Resolve the widget iframe by the PANEL ROOT, not the composer: some widget variants (a
    # "help center" Home) render no composer until you enter a conversation, so keying off the
    # composer would be chicken-and-egg (the composer only appears after clicking the entry,
    # which needs the frame). The panel root is present on the Home screen of every variant.
    widget_frame_marker=".tawk-chat-panel",
    confirm_setup_js=("window.__cw_confirm = window.__cw_confirm || [];"
                      " try { window.Tawk_API.onChatMessageVisitor = function(m) {"
                      " window.__cw_confirm.push(typeof m === 'string' ? m : JSON.stringify(m)); }; }"
                      " catch(e) {}"),
)


class TawkAdapter:
    vendor = "tawk.to"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        return WidgetDriver(TAWK).send(domain, pitch, reply_email)
