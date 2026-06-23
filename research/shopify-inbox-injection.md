# Research: Shopify Inbox injection (#8) - findings 2026-06-22

Goal: an Adapter that injects the Pitch into the Shopify Inbox storefront chat. This is
the volume vendor (#2: 49,162 apparel stores, ~17x Gorgias).

## Key finding: NO JS API (unlike Gorgias)
- `window.ShopifyChat` exists but is the custom-element CLASS, not an API object. Its
  prototype is only `{constructor, connectedCallback}` - there is no `sendMessage` /
  `open` to script. The clean GorgiasChat approach does NOT transfer.
- The widget mounts as `<shopify-chat>` / `#shopify-chat` (a div). The launcher + chat
  panel are injected by the element; the panel renders in a CROSS-ORIGIN iframe from
  `shopify-chat.shopifyapps.com` once opened.
- Therefore the Adapter must drive the DOM/iframe: open launcher -> handle the email
  gate -> type into the composer -> click send. Playwright's frame API can reach the
  cross-origin chat iframe.

## What did not work (so the next session does not repeat it)
- Headless: clicking the `#shopify-chat` mount div directly did NOT inject the chat
  iframe on any of naot.com / willleathergoods.com / albertonardoni.com (no
  shopifyapps frame appeared). The real launcher element / open flow needs more work,
  and likely needs a headed (visible) browser and a real click on the rendered launcher
  button (which the custom element draws), possibly with the customer-info (name/email)
  form appearing first.

## Detection + targets
- Signature (from signatures.py): script `shopify-chat.shopifyapps.com` /
  `messaging-api.shopifyapps.com`; runtime global `ShopifyChat`; selectors `#shopify-chat`,
  `shopify-chat`.
- Static HTML check found Shopify Inbox currently live on ~7.5% of a 40-store sample of
  the StoreLeads "installed" list. This UNDERCOUNTS: the script often injects via JS, so a
  browser-rendered (layer2) check will find many more. StoreLeads app data is also somewhat
  stale, so re-detect live before pitching.
- Targets: 49,162 domains in `/tmp/shopify_inbox_targets.json` (from StoreLeads apparel).
- Confirmed currently-live TEST stores: **naot.com, willleathergoods.com, albertonardoni.com**.

## Adapter plan (ShopifyInboxAdapter.send)
1. goto site; wait for `window.ShopifyChat` / `#shopify-chat`.
2. Click the REAL launcher (find the rendered button; do it headed first to see it).
3. Handle the customer-info gate: fill the reply email (and any required name).
4. Type the Pitch into the composer (contenteditable/textarea inside the chat iframe).
5. Click send. Return SendResult(sent, detail).
6. Drive the `shopify-chat.shopifyapps.com` iframe via Playwright `frame_locator`.
- Build headed to iterate on selectors; verify with a HITL live send (like Gorgias).
- It slots behind the existing Adapter interface (#5): register under vendor
  "shopify-inbox" in the adapters dict; nothing else in the engine changes.

## Reply path: already solved
Shopify Inbox auto-emails the agent reply to the address given at the gate (research/
reply-delivery.md), so the one-inbox Reply Watcher works unchanged.
