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
Tried (committed): popup-dismissal (Escape + close buttons) + `tidioChatApi.open()` + a
launcher-click fallback. STILL fails on lagarconne.com (newsletter modal) and shoshanna.com
(cookie-consent banner): the panel does NOT expand (stays a collapsed bubble) -> no composer.

So the real blocker is **reliably OPENING the Tidio panel**, not finding the composer. The
generic open is not landing. The focused debugging pass should:
1. Inspect the open behavior on ONE store live: after `tidioChatApi.open()`, dump the FULL
   frame tree + every textarea/contenteditable/input with its frame URL, to learn the exact
   chat-window iframe + composer element (the composer may be a contenteditable, not a textarea).
2. Handle the site overlays that block the launcher (cookie/consent banners + newsletter modals)
   BEFORE opening - accept/close them, not just Escape.
3. Confirm `tidioChatApi` actually opens the panel in automation (it may need the widget more
   initialized, a real launcher click on the bubble at its coordinates, or `display(true)`).
4. Then type into the real composer, send, handle optional pre-chat form, live-verify delivery.

This needs hands-on live frame inspection (like the Shopify Inbox reverse-engineering), not
blind selector guessing. Best done as a short dedicated pass.

## Test stores
40 live Tidio domains in /tmp/tidio_live.json. shoshanna.com confirmed tidioChatApi=object;
ninjatransfers.com composer reachable + captcha=false (but has a quick-reply bot).
