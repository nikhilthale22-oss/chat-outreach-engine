# Research: Tidio injection (#8 pivot) - 2026-06-23

Tidio is the chosen pivot vendor after Shopify Inbox turned out CAPTCHA-walled.

## Why Tidio
- ~2,911 apparel stores (StoreLeads); **80% currently live** on a 50-store check (vs Shopify
  Inbox's 7.5%) - durable + statically detectable (code.tidio.co in HTML).
- **Verified automatable:** `window.tidioChatApi` is present (typeof object), and the send
  flow has **NO CAPTCHA** (probed ninjatransfers.com composer: captcha=false). This is the
  decisive contrast with Shopify Inbox.
- The engine detects + routes Tidio correctly (CLI on lagarconne.com -> vendor=tidio ->
  TidioAdapter), and the Ledger left a failed send at Queued (retryable, no spam).

## First-cut adapter status (adapters/tidio.py)
Opens via `tidioChatApi.open()`, scans frames for the composer `textarea`, types, presses
Enter; fills an optional pre-chat email; no CAPTCHA to solve. WORKS as far as detect/route/
open-call, but on lagarconne.com the chat panel did not visibly open (a newsletter modal
covered the page) so the composer was not found -> send_failed:no_composer (correctly Queued).

## Next iteration to finish it (the clear next step)
1. Dismiss site marketing popups before opening (Escape + common close buttons).
2. Make the open reliable: retry `tidioChatApi.open()`, and fall back to clicking the
   `#tidio-chat-iframe` launcher; wait for the chat window iframe.
3. Locate the composer textarea inside the Tidio chat-window iframe (not the launcher iframe).
4. Handle an optional Tidio pre-chat form (name/email) if the merchant enabled one.
5. Live-verify on a few stores (delivery + reply lands in the inbox).

## Test stores
40 live Tidio domains in /tmp/tidio_live.json. shoshanna.com confirmed tidioChatApi=object;
ninjatransfers.com composer reachable + captcha=false (but has a quick-reply bot).
