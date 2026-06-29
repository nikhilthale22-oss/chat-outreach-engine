"""ReamazeAdapter: the Adapter for Re:amaze (Reamaze) chat widgets.

Re:amaze is DOM-drive (a VendorConfig over WidgetDriver, ADR-0007), established by live probes
(research/crisp-reamaze-injection.md), which overturned the earlier "defer Re:amaze" call:

- The embed sets window._support (config) and lazily loads the SDK as window.Reamaze. The SDK can be
  slow to appear, so the ready gate waits on window.Reamaze with a long timeout.
- Open with Reamaze.popup() (the earlier guess Shoutbox()/popup-verb confusion was the blocker). The
  conversation renders in a same-origin about:blank iframe with NO stable URL (Tawk-style), so the
  driver resolves that frame by content - the composer <textarea placeholder="Enter your question or
  message here">, which exists only inside that frame.
- One-way model: email_strategy="none" (we only deliver; the pitch carries our links). Confirm via
  dom_echo (sent message echoes into the thread and clears the composer).
- Coverage caveat: the static "Re:amaze" tag over-counts and the SDK is lazy, so a fraction of tagged
  stores never bring up window.Reamaze in time (they return no_reamaze_api); measured reach is lower
  than the raw tag count.
"""
from __future__ import annotations

from ..injector import SendResult
from ..widget_driver import VendorConfig, WidgetDriver

# The Re:amaze composer placeholder is stable user-facing copy and lives only inside the widget's
# about:blank iframe, so it serves as both the frame marker and the composer selector.
_COMPOSER = "textarea[placeholder*='question or message' i]"

REAMAZE = VendorConfig(
    vendor="reamaze",
    widget_scope=None,                       # the resolved iframe IS the scope
    ready_predicate="window.Reamaze",
    ready_fallback_predicate="window.Reamaze",
    ready_timeout_ms=30000,                  # the SDK loads lazily; give it room
    not_ready_detail="no_reamaze_api",
    open_js="try{window.Reamaze && Reamaze.popup && Reamaze.popup()}catch(e){}",
    entry_labels=("Start a conversation", "Send us a message", "Chat", "Contact us"),
    email_strategy="none",
    email_api_js=None,
    confirm_strategy="dom_echo",
    confirm_frame_marker=None,
    composer_selector=_COMPOSER,
    entry_selector="button, [role='button']",
    entry_strategy="by_text",
    widget_frame_marker=_COMPOSER,           # resolve the about:blank iframe by the composer marker
)


class ReamazeAdapter:
    vendor = "reamaze"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        return WidgetDriver(REAMAZE).send(domain, pitch, reply_email)
