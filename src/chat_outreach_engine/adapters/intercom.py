"""IntercomAdapter: Adapter for Intercom (API-send, ADR-0007).

Intercom transmits a visitor message via a single JS call - `Intercom('startConversation', message)`
"immediately sends the message and starts the conversation" (its showNewMessage only PRE-fills the
composer). So Intercom is an ApiVendorConfig over ApiSendDriver, not a DOM-drive WidgetDriver config.

STATUS: wired, NOT send-verified. The startConversation send path has not been confirmed by a real
merchant pitch yet (no unattended real sends). dom_echo_any confirms by the message rendering in the
Intercom Messenger.
"""
from __future__ import annotations

from ..api_send_driver import ApiSendDriver, ApiVendorConfig
from ..injector import SendResult

INTERCOM = ApiVendorConfig(
    vendor="intercom",
    ready_predicate="window.Intercom",
    ready_fallback_predicate="window.intercomSettings",
    ready_timeout_ms=20000,
    not_ready_detail="no_intercom",
    open_js="window.Intercom('show')",
    send_js="window.Intercom('startConversation', m)",
    confirm_strategy="dom_echo_any",
)


class IntercomAdapter:
    vendor = "intercom"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        return ApiSendDriver(INTERCOM).send(domain, pitch, reply_email)
