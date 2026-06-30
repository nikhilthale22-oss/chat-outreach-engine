"""ZohoSalesIQAdapter: the Adapter for Zoho SalesIQ chat widgets.

Zoho SalesIQ is DOM-drive (a VendorConfig over WidgetDriver, ADR-0007), established by live probes
(research/widget-vendor-spike.md):

- SDK is window.$zoho.salesiq. Ready predicate: window.$zoho && window.$zoho.salesiq.
- Open with $zoho.salesiq.floatwindow.visible('show') and chat.start() (skins differ on which one
  surfaces the composer, so we fire the float-window, float-button, and chat.start verbs, each guarded).
- Zoho renders its chat UI in an iframe WITH NO STABLE URL (an `about:blank` frame), so the composer
  cannot be reached page-level. The driver resolves that frame by an in-frame content marker
  (widget_frame_marker) and scopes the composer to it - the same about:blank-frame mechanism the
  engine already uses for Tawk. The composer is <textarea id="msgarea"> ("Type your message and hit
  'Enter'").
- One-way model: email_strategy="none" (we do not rely on an inbound reply). Confirm via dom_echo:
  the sent message echoes into the transcript and the composer clears.
- Coverage caveat: the static "zoho-salesiq" tech tag over-counts; only stores whose $zoho.salesiq SDK
  actually loads and mounts the chat frame pass (others return no_zoho_api / no_composer).
"""
from __future__ import annotations

from ..injector import SendResult
from ..widget_driver import VendorConfig, WidgetDriver

# The message box is <textarea id="msgarea">; some skins drop the id, so we also accept a message-
# placeholder textarea. This doubles as the in-frame marker that resolves Zoho's about:blank frame.
_COMPOSER = "textarea#msgarea, textarea[placeholder*='message' i]"

ZOHO_SALESIQ = VendorConfig(
    vendor="zoho-salesiq",
    widget_scope=None,                       # scoped to the resolved widget frame, not the page
    ready_predicate="window.$zoho && window.$zoho.salesiq",
    ready_fallback_predicate="window.$zoho && window.$zoho.salesiq",
    ready_timeout_ms=20000,
    not_ready_detail="no_zoho_api",
    open_js=("try{$zoho.salesiq.floatwindow.visible('show')}catch(e){};"
             "try{$zoho.salesiq.floatbutton.visible('show')}catch(e){};"
             "try{$zoho.salesiq.chat.start()}catch(e){}"),
    entry_labels=(),
    email_strategy="none",
    email_api_js=None,
    confirm_strategy="dom_echo",
    confirm_frame_marker=None,
    composer_selector=_COMPOSER,
    entry_selector="button, [role='button']",
    entry_strategy="by_text",
    widget_frame_marker=_COMPOSER,           # Zoho's chat frame is about:blank - resolve by content
)


class ZohoSalesIQAdapter:
    vendor = "zoho-salesiq"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        return WidgetDriver(ZOHO_SALESIQ).send(domain, pitch, reply_email)
