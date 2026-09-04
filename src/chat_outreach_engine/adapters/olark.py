"""OlarkAdapter: the Adapter for Olark chat widgets.

Olark is DOM-drive (a VendorConfig over WidgetDriver, ADR-0007), established by live probes
(research/widget-vendor-spike.md):

- SDK is window.olark (the classic command API). Ready predicate: window.olark.
- Open with olark('api.box.expand') (older skins answer api.box.show, so we fire both, each guarded).
  Olark injects its chatbox INTO THE HOST PAGE DOM (a same-origin storage.html iframe exists but only
  holds state, not the composer), so the composer is a page-level <textarea> with a generated id
  prefixed `olark-custom-element-`; no frame resolution needed.
- When the team is OFFLINE (common for Olark's smaller merchants) the widget shows a "leave a message"
  survey: REQUIRED Name + Email inputs + the message textarea + a SEND button (all inside
  #olark-container, class olark-offline-survey). We reach that box, so email_strategy="contact_form":
  the driver fills name/email/message and clicks SEND (proven live on bfyne.com, 2026-07-19). Online,
  no email/submit survey is present, so _is_contact_form is False and it falls back to the live send.
- widget_scope="#olark-container": Olark renders in the PAGE DOM, so without a scope the contact-form
  field-finder would grab the page's own newsletter email input. Scoping every field/submit lookup to
  the Olark container keeps us on the widget's own name/email/message/SEND.
- Coverage caveat: the static "Olark" tech tag over-counts; only stores whose olark SDK actually loads
  pass the ready gate (others return no_olark_api).
"""
from __future__ import annotations

from ..injector import SendResult
from ..widget_driver import VendorConfig, WidgetDriver

# Olark's message box is a <textarea> whose id is generated as `olark-custom-element-#N` (N shifts
# with how many inline pre-chat fields the skin shows), so the id PREFIX is the durable composer
# marker - and it only matches the textarea, never the name/email <input>s that share the prefix.
_COMPOSER = "textarea[id^='olark-custom-element']"

OLARK = VendorConfig(
    vendor="olark",
    widget_scope="#olark-container",         # page-DOM widget: scope field-finding to its own box
    ready_predicate="window.olark",
    ready_fallback_predicate="window.olark",
    ready_timeout_ms=20000,
    not_ready_detail="no_olark_api",
    open_js=("try{olark('api.box.expand')}catch(e){};"
             "try{olark('api.box.show')}catch(e){}"),
    entry_labels=(),                         # open lands directly on the composer (no Home screen)
    email_strategy="contact_form",           # offline: fill the leave-a-message Name/Email/Message + SEND
    email_api_js=None,
    confirm_strategy="dom_echo",             # online fallback; offline confirms via _form_confirmed
    confirm_frame_marker=None,
    composer_selector=_COMPOSER,
    entry_selector="button, [role='button']",
    entry_strategy="by_text",
    widget_frame_marker=None,
)


class OlarkAdapter:
    vendor = "olark"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        return WidgetDriver(OLARK).send(domain, pitch, reply_email)
