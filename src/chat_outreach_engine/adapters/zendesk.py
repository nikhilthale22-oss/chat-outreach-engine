"""ZendeskAdapter: the Adapter for Zendesk chat widgets.

Zendesk is DOM-drive, not api-send, so it is a VendorConfig (ZENDESK) over the shared WidgetDriver
(ADR-0007). Established by live probes against real stores (research/zendesk-injection.md), which
overturned the earlier "defer Zendesk" call:

- Two widget families exist. The MODERN "messaging" widget dominates (Zendesk deprecated the Classic
  Web Widget), so this config targets it. It renders its conversation panel in a same-origin
  srcdoc/blank iframe titled "Messaging window" (no stable URL or id), Tawk-style, so the driver
  resolves that frame by content: the frame containing the composer `textarea[placeholder="Type a
  message"]`. The Classic Web Widget (iframe#webWidget, a name+email+message pre-chat form) is a
  minority and a separate future variant.
- zE has no one-call visitor-send (modern send is an async newConversation->sendMessage), so a
  visitor message is DOM-driven: open the panel, type into the composer, Enter. open_js fires every
  open verb (messenger/webWidget/activate), each guarded, so the right one runs whatever family it is.
- No pre-chat email gate on the messaging composer (email is collected mid-conversation, if at all),
  so email_strategy="none". Confirm via dom_echo: the sent message echoes into the thread and clears
  the composer (same as Tawk - reliable, no false positives).
- Coverage caveat: only stores whose static.zdassets.com/ekr/snippet.js loader is actually served
  pass the live gate; the snippet tag lingers after an account lapses (the loader then 40x's), and
  many grep-matched stores no longer run Zendesk at all (the static signature over-counts).
"""
from __future__ import annotations

from ..injector import SendResult
from ..widget_driver import VendorConfig, WidgetDriver

# The messaging composer placeholder is stable user-facing copy; Zendesk obfuscates class names, so
# the placeholder is the most durable marker for both the widget frame and the composer itself.
_COMPOSER = "textarea[placeholder='Type a message' i]"

ZENDESK = VendorConfig(
    vendor="zendesk",
    widget_scope=None,                       # the resolved iframe IS the scope
    ready_predicate="window.zE",
    ready_fallback_predicate="window.zE",
    ready_timeout_ms=20000,
    not_ready_detail="no_zendesk_api",
    # Fire every open verb, each guarded, so the call that matches this store's family runs and a
    # throw on the others (e.g. webWidget.open on a messaging-only widget) does not block the rest.
    open_js=("try{window.zE('messenger','open')}catch(e){};"
             "try{window.zE('webWidget','open')}catch(e){};"
             "try{window.zE.activate&&window.zE.activate()}catch(e){}"),
    entry_labels=("Live chat", "Chat with us", "Start chat", "Send us a message"),
    email_strategy="none",
    email_api_js=None,
    confirm_strategy="dom_echo",
    confirm_frame_marker=None,
    composer_selector=_COMPOSER,
    entry_selector="button, [role='button']",
    entry_strategy="by_text",
    widget_frame_marker=_COMPOSER,
)


class ZendeskAdapter:
    vendor = "zendesk"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        return WidgetDriver(ZENDESK).send(domain, pitch, reply_email)
