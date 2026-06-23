# Research: Tidio injection (#8) - SOLVED 2026-06-23 (2nd live vendor)

Tidio is the pivot vendor after Shopify Inbox turned out CAPTCHA-walled. It is now a
**live, wire-confirmed working Adapter** (adapters/tidio.py). Below is the reverse-engineering
trail and the exact proven flow, so this never has to be rediscovered.

## The widget shape (what took the longest to see)
- Tidio's widget renders in **OPEN SHADOW DOM** under one host: `div#tidio-chat`. Playwright
  pierces open shadow roots, so the iframe-only scans (page.frames) found NOTHING - the panel
  was never in an iframe. `document.querySelector('textarea')` is also null (shadow), but a
  Playwright locator finds it. **Scope everything to `#tidio-chat`** - unscoped
  `input[placeholder*=email]` matches 3 fields (1 Tidio + 2 the site's Klaviyo newsletter);
  `#tidio-chat input[type=email]` matches exactly the 1 right one.
- `messageFromVisitor()`/`messageFromOperator()` are **UI-simulation only** - they never put the
  message on the wire (proved by capturing websocket frames: only visitorIsTyping / analytics,
  never a message event). Do NOT use them to send.

## The proven send flow (what adapters/tidio.py does)
1. goto; wait for `window.tidioChatApi.readyEventWasFired === true` (<=25s). If it never loads ->
   `no_tidio_api` (retryable).
2. `tidioChatApi.open()`; dismiss page-level overlays (newsletter/consent) that can obscure the
   widget's fields - scoped OUTSIDE `#tidio-chat` so we never close the chat itself.
3. If no composer yet (Home screen), click an entry button ("Chat with us" etc.) inside the widget.
4. Type the pitch into the `#tidio-chat textarea`, sending **newlines as Shift+Enter** (soft line
   breaks), then one final Enter to send. THIS MATTERS: a raw `\n` typed as Enter submits early
   and spills the rest of the pitch into the next focused field (it landed in the pre-chat email
   box and failed @-validation - caught via the debug screenshot).
5. Pre-chat gate (if the merchant enabled one): clear+fill `#tidio-chat input[type=email]` with the
   reply email (force=True to beat transient overlay hit-tests), click the widget's Send. The held
   message then flushes. If no pre-chat, attach the email via `setContactProperties({email})`.
6. **Delivery is confirmed on the wire:** a real send emits a `visitorNewMessage` frame carrying the
   text + a server messageId. The adapter captures framesent and only returns sent=True when it sees
   that frame contain a distinctive token from the pitch. **No false positives.** (My first naive
   attempt returned "sent" with zero delivery - the wire check is what makes SendResult honest.)

## Live proof (2026-06-23)
`HEADED/headless python -m chat_outreach_engine.cli talleyandtwine.com --send --email
nikhilthale18@gmail.com` -> `pitched - sent`, wire frame:
`visitorNewMessage {"message":"Hey, saw you don't have an AI chatbot ...","messageId":"40b7da6e-..."}`.
Debug screenshot: full pitch in the conversation, email captured, "we're currently unavailable,
leave your email" operator auto-reply. NO CAPTCHA anywhere in the flow.

## Coverage caveat (for the batch runner)
Only stores that embed Tidio via a **direct `code.tidio.co/<id>.js` script tag** initialise the API
under automation. Stores that inject Tidio via a Shopify app-embed / GTM (only `tidioChatApi`
referenced, no direct tag) do NOT load it headless OR headed -> `no_tidio_api`, retryable.
The /tmp/tidio_live.json scan also has false positives (ninjatransfers.com has no Tidio at all).
**The batch runner must re-confirm `code.tidio.co/<id>.js` in the live HTML before counting a store
as a Tidio target**, else coverage is inflated.

## Test stores
talleyandtwine.com (direct tag, pre-chat enabled, API loads instantly - the proven store).
shoshanna.com (real Tidio but consent-gated: loads only after cookie-consent accepted).
mulberryparksilks.com (dynamic Shopify app-embed - does NOT load under automation).
