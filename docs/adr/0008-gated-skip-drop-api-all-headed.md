# 0008 - Gated vendors are skipped; API send dropped; all-headed

Date: 2026-07-17
Status: Accepted

## Context

- Shopify Inbox (our biggest vendor, and the 2026-07-16 browserless "crack") now requires buyer
  sign-in: a live re-check found 13/13 sampled stores with `require_buyer_shop_sign_in=True` and
  `reply_by_email_available=False`. The anonymous send no longer clears the gate.
- No API-send vendor is proven end to end: Gorgias's chat widget is off on ~all tagged stores (0/140
  expose `window.GorgiasChat`; the tag is a helpdesk tag), Intercom is wired-but-unverified and
  AI-fronted (Fin) + B2B-skewed, and Shopify is now gated. The `send/api/` bucket is empty of anything real.
- The goal is pure volume, and the operator is non-technical.

## Decision

1. **Gated = skip.** If a store requires sign-in, an unsolvable captcha, or fields we cannot fill,
   mark it skipped and move on. Never fight a locked door. Shopify Inbox + shopify-agent -> skip.
2. **Drop the API send path.** Remove Gorgias/Intercom from the active route registry. `send/api/`
   is parked (not deleted) but not wired into the pipeline.
3. **All-headed.** The only active send method is `headed` = drive the store's real chat widget in a
   browser (the human live-chat vendors: Tawk, Crisp, Zendesk, LiveChat, Chatra, HelpScout, Olark,
   Zoho SalesIQ, Tidio, Re:amaze).
4. **Registry is proven-only.** A vendor earns a spot in `route/registry.VENDOR_METHOD` only after it
   delivers end to end, live, confirmed to Nikhil. It grows one vendor at a time.

## Consequences

- Coverage lost by dropping API is ~zero (those vendors were ~0 real). Accuracy goes UP: every
  successful send is a genuine support message we can screenshot, not an unconfirmed JS call.
- Throughput is now bounded by browser cost (~15-30s/store) -> ~12 parallel browsers + rotating
  residential IPs for 50k/day (Phase 4).
- The reachable pool shrinks to ungated human-widget stores (Shopify, the biggest slice, is skipped).
  Pool size, not speed, may be the binding constraint. The contact form (~6% captcha-free, the
  universal door) is the bigger-volume lever, deferred.
