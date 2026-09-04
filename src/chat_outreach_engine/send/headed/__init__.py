"""Phase 3 - Send / headed: the browser-driven vendors and their adapters.

The only active send method (ADR-0008, all-headed): drive the real chat widget in a browser.
`build_headed_adapters()` is the canonical vendor -> adapter map the Pipeline dispatches a
`headed`-routed store to. Vendor keys match route.registry.VENDOR_METHOD. Each adapter is a
VendorConfig over the shared WidgetDriver (ADR-0007). The adapter modules still physically live
under `adapters/`; relocating the files here is mechanical reshape tracked separately - this
registry is the single place the headed cards are assembled.
"""
from __future__ import annotations

from ...adapters import (ChatraAdapter, CrispAdapter, HelpScoutAdapter, HubSpotAdapter,
                         LiveChatAdapter, OlarkAdapter, ReamazeAdapter, TawkAdapter, TidioAdapter,
                         ZendeskAdapter, ZohoSalesIQAdapter)

# vendor key -> adapter class. One source of truth for the headed family (the same map is still
# duplicated inside cli.py + batch_cli.py for now; those move onto this later).
_HEADED_ADAPTER_CLASSES = {
    "tawk.to":      TawkAdapter,
    "crisp":        CrispAdapter,
    "tidio":        TidioAdapter,
    "zendesk":      ZendeskAdapter,
    "livechat":     LiveChatAdapter,
    "chatra":       ChatraAdapter,
    "helpscout":    HelpScoutAdapter,
    "hubspot-chat": HubSpotAdapter,
    "olark":        OlarkAdapter,
    "zoho-salesiq": ZohoSalesIQAdapter,
    "reamaze":      ReamazeAdapter,
}


def build_headed_adapters() -> dict:
    """A fresh {vendor: adapter instance} for every headed vendor. Adapters are stateless
    (a VendorConfig wrapper over WidgetDriver), so a new map per run is cheap and shares no state."""
    return {vendor: cls() for vendor, cls in _HEADED_ADAPTER_CLASSES.items()}


__all__ = ["build_headed_adapters"]
