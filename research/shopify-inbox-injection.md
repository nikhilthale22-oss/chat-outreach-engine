# Research: Shopify Inbox injection (#8)

> ## UPDATE 2026-06-29 - UNLOCKED. The 2026-06-23 "CAPTCHA-walled, parked" conclusion below was WRONG.
>
> The blocker call concluded from the captcha being PRESENT (the form is labelled "protected by
> hCaptcha" and once carried g-recaptcha/h-captcha fields) without testing whether it ENFORCES. It does
> not, at low volume: that hCaptcha is **invisible/passive** (no "I'm not a robot" checkbox). A real
> HITL test filled the contact form (First/Last/Email), clicked Start chat, and the message **POSTED to
> the thread with NO challenge** - from a HEADLESS browser on a DATACENTER IP (the worst case for passive
> scoring). Real delivered sends: **pickityplace.com** (raw flow) and **brandingirons.com** (via the
> shipped `ShopifyInboxAdapter`, screenshot-confirmed). 6/8 of a fresh random sample reached the composer.
>
> So Shopify Inbox IS automatable, free (no captcha solver at low volume), and is the count leader.
> The current widget: `<inbox-online-store-chat>` OPEN shadow DOM (Playwright CSS pierces it; NOT the
> old cross-origin `shopify-chat.shopifyapps.com` iframe). Flow: open -> composer `textarea` (data-spec
> `message-input`, placeholder "Write message") -> click Send (data-spec `message-submit`) -> the
> "Before we get started" form (First/Last/Email + opt-in) -> Start chat -> message posts. Confirm =
> dom_echo (token in the rendered thread). Bonus: the form REQUIRES email = a built-in reply path.
>
> Built as `adapters/shopify_inbox.py` (its OWN class per ADR-0007; honest `_verdict`: delivered only on
> token-in-thread, `captcha_challenge` if passive ever flags us, `form_blocked` otherwise). OPEN: the
> static SignatureDetector misses Shopify Inbox (JS-injected), so the engine needs a browser-layer
> detect pass (or a known-SI-list run) to route stores here - the adapter self-detects via
> `no_shopify_inbox`. Also unproven at scale: the invisible-hCaptcha pass-RATE (N≈2) and reply-capture.
> LESSON: a captcha being present is not a captcha being enforced - test the actual submission.

## (historical) findings 2026-06-22

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

## BLOCKER (found 2026-06-23 by live test): CAPTCHA on the first message
Verified end to end on naot.com (headed). The flow is: open launcher -> type into
`textarea[data-spec=message-input]` -> click `button[data-spec=message-submit]`. But the
first message from a new visitor then surfaces a customer-info form (First name, Last name,
Email Address, "Start chat" submit) that contains **`g-recaptcha-response` AND
`h-captcha-response`** fields - i.e. it is CAPTCHA-gated. The message does NOT deliver until
that form is completed and the CAPTCHA passes.

The ShopifyInboxAdapter (adapters/shopify_inbox.py) correctly opens/types/sends and tries to
fill the email, but it CANNOT pass the CAPTCHA, so it does not reliably deliver. Verified
visually: after "send", the form stayed up with empty fields (no pitch delivered - so the
live test did NOT spam naot.com, good).

### Conclusion - Shopify Inbox is NOT the easy volume win the count implied
Raw count (49,162) ranked it #1, but new-conversation injection is CAPTCHA-walled. Solving
that at scale = captcha-solver / anti-bot territory (sketchy, costly, fragile). So:
- **Park Shopify Inbox** for automated injection unless we accept a captcha-solving service.
- **Pivot the next Adapter to a vendor without a CAPTCHA gate**, ideally with a JS API like
  Gorgias had: **Crisp** (`$crisp.push(["do","message:send",...])` - clean API, count ~145) or
  **Tidio** (~2,911, the real volume tier, DOM-based, sends immediately, email optional).
- General lesson: vendor pick should weight *automatability* (clean API, no CAPTCHA), not just
  store count. Gorgias was easy because of its JS API; the count leader is the hardest.

## Reply path: already solved
Shopify Inbox auto-emails the agent reply to the address given at the gate (research/
reply-delivery.md), so the one-inbox Reply Watcher works unchanged - IF a message ever
gets past the CAPTCHA.
