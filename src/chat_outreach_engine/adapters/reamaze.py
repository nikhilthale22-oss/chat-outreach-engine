"""ReamazeAdapter: the Adapter for Re:amaze (Reamaze) chat widgets.

STATUS (2026-06-29): BUILT BUT NOT YET WORKING AT SCALE - do not rely on it. Verify-to-composer
measured 0/15: Reamaze.popup() opens a MENU ("Contact Us" / "Contact Us Directly" / "Find an order"),
not the composer, so the composer sits behind an entry click AND the about:blank widget frame cannot
be resolved by the composer marker (it is not present at the menu stage). Some stores also bring up no
frame at all in the window. The remaining work (its own spike): resolve the about:blank frame by a
MENU-stage marker, click the "Contact Us Directly"/"Send us a message" entry inside it, then drive the
revealed composer. Crisp shipped fine; Re:amaze is parked here with the mechanics captured.

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
