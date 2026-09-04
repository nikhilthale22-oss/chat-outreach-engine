"""Phase 2 - Route: the per-vendor "card".

Maps a detected vendor to HOW we can send, or marks it gated (skip). This is the one
place a vendor's routing lives: add a vendor by extending VENDOR_METHOD, retire one by
moving it to GATED_VENDORS. The machine's shape never changes - only these tables.
"""

METHOD_API = "api"        # browserless HTTP (fast, scales)
METHOD_HEADED = "headed"  # drive a real browser (slower, needs a clean IP)
METHOD_FORM = "form"      # the store's native contact form (deferred)

# Vendors we can deliver to today, and by which method. ADR-0008: the registry is proven-only
# and ALL-HEADED - API send is dropped (0 vendors proven end to end: Gorgias chat is off on ~all
# tagged stores, Intercom is AI-fronted + wired-only, Shopify Inbox is sign-in gated). Gorgias and
# Intercom are therefore NOT routed here; with no card they fall through to no_method (skip), like
# any unsupported vendor. Re-add a vendor only after it delivers live. headed = human live-chat /
# helpdesk widgets driven in a real browser.
VENDOR_METHOD = {
    "tawk.to":      METHOD_HEADED,
    "crisp":        METHOD_HEADED,
    "tidio":        METHOD_HEADED,
    "zendesk":      METHOD_HEADED,
    "livechat":     METHOD_HEADED,
    "chatra":       METHOD_HEADED,
    "helpscout":    METHOD_HEADED,
    "hubspot-chat": METHOD_HEADED,
    "olark":        METHOD_HEADED,
    "zoho-salesiq": METHOD_HEADED,
    "reamaze":      METHOD_HEADED,
}

# Vendors that gate sending (sign-in / unsolvable). Skip on sight, never attempt.
# Shopify Inbox + agent require a signed-in buyer (13/13 checked 2026-07-17). See PLAN "Gated = skip".
GATED_VENDORS = {
    "shopify-inbox",
    "shopify-agent",
    "shopify-ai-chat",
}
