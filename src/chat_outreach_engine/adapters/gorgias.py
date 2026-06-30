"""GorgiasAdapter: Adapter for Gorgias chat (API-send, ADR-0007).

Gorgias transmits a visitor message via a JS call - window.GorgiasChat.sendMessage(text) - after
capturing the visitor email at the gate (captureUserEmail). There is no composer to type into, so
Gorgias is an ApiVendorConfig over ApiSendDriver, the same family as Intercom. This REPLACES the older
hand-written class that returned an optimistic "pitch_sent" the moment sendMessage was called, with no
proof the message posted; ApiSendDriver confirms by dom_echo_any (our Pitch token must render in the
Messenger) and so returns "delivered" / "no_delivery_confirmation" honestly.

CRITICAL COVERAGE NOTE (measured 2026-06-30, research/gorgias-chat-verification.md): the StoreLeads
"Gorgias" tag flags the Gorgias HELPDESK / contact-forms PLATFORM, not the on-site chat widget. Most
tagged stores expose only window.GorgiasBridge (the bundle-loader, used for email/contact forms) and
have the live CHAT widget OFF - they never expose window.GorgiasChat, so this adapter correctly
returns no_gorgias_chat. The drivable chat pool is the CHAT-LIVE subset, far smaller than the tag count.
Re-qualify a Gorgias list with research/gorgias_chatlive.py before pitching.

STATUS: send path migrated to the confirming driver but NOT yet proven by a real send (HITL).
"""
from __future__ import annotations

from ..api_send_driver import ApiSendDriver, ApiVendorConfig
from ..injector import SendResult

GORGIAS = ApiVendorConfig(
    vendor="gorgias",
    ready_predicate="window.GorgiasChat",
    ready_fallback_predicate="window.GorgiasChat",
    ready_timeout_ms=20000,
    not_ready_detail="no_gorgias_chat",
    # init() boots the chat bundle, open() shows it; fired sync (we cannot await in open_js), the
    # driver's post-open settle covers the boot before the send.
    open_js=("try{var _r=window.GorgiasChat.init&&window.GorgiasChat.init();}catch(_){}"
             ";try{window.GorgiasChat.open&&window.GorgiasChat.open();}catch(_){}"),
    # capture the reply email at the gate, then transmit; m=Pitch, e=reply email.
    send_js=("try{window.GorgiasChat.captureUserEmail&&window.GorgiasChat.captureUserEmail(e);}catch(_){}"
             ";window.GorgiasChat.sendMessage(m)"),
    confirm_strategy="dom_echo_any",
)


class GorgiasAdapter:
    vendor = "gorgias"

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        return ApiSendDriver(GORGIAS).send(domain, pitch, reply_email)
