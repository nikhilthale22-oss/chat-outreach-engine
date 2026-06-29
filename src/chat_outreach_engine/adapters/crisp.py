"""CrispAdapter: the Adapter for Crisp chat widgets.

Crisp is DOM-drive (a VendorConfig over WidgetDriver, ADR-0007), established by live probes
(research/crisp-reamaze-injection.md), which overturned the earlier "drop Crisp" call:

- SDK is window.$crisp (the array-push API). Ready predicate: window.$crisp.
- Open with $crisp.push(['do','chat:open']) (some skins want chat:show first, so we fire both, each
  guarded). Crisp injects its chatbox INTO THE HOST PAGE DOM (not an iframe), so the composer is a
  page-level <textarea placeholder="Compose your message...">; no frame resolution needed.
- One-way model: we only need to DELIVER the pitch (it carries our links), so email_strategy="none"
  - Crisp can attach an email via $crisp set user:email, but we do not rely on an inbound reply.
  Confirm via dom_echo: the sent message echoes into the conversation and clears the composer.
- Coverage caveat: the static "Crisp" tech tag over-counts; only stores whose $crisp SDK actually
  loads pass the ready gate (others return no_crisp_api).
"""
from __future__ import annotations

from ..injector import SendResult
from ..widget_driver import VendorConfig, WidgetDriver

# Crisp's default composer placeholder is stable English copy; the class names are hashed, so the
# placeholder is the most durable composer marker. (Non-English Crisp skins localise it - a future
# variant; the vast majority are English.)
_COMPOSER = "textarea[placeholder*='Compose your message' i]"

CRISP = VendorConfig(
    vendor="crisp",
    widget_scope=None,                       # Crisp renders in the page DOM, not an iframe
    ready_predicate="window.$crisp",
    ready_fallback_predicate="window.$crisp",
    ready_timeout_ms=20000,
    not_ready_detail="no_crisp_api",
    open_js=("try{$crisp.push(['do','chat:show'])}catch(e){};"
             "try{$crisp.push(['do','chat:open'])}catch(e){}"),
    entry_labels=(),                         # open lands directly on the composer (no Home screen)
    email_strategy="none",
    email_api_js=None,
    confirm_strategy="dom_echo",
    confirm_frame_marker=None,
    composer_selector=_COMPOSER,
    entry_selector="button, [role='button']",
    entry_strategy="by_text",
    widget_frame_marker=None,
)


class CrispAdapter:
    vendor = "crisp"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        return WidgetDriver(CRISP).send(domain, pitch, reply_email)
