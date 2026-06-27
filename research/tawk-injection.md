# Research: tawk.to injection (spike, 2026-06-27)

Reverse-engineered live against 3 real Tawk apparel stores (probes on Server #1, no messages sent):
fossilageminerals.com, allurepack.com (default widget), mohifashion.com (custom widget id). Cross-checked
against the official JS API docs (developer.tawk.to) via a recon workflow.

## Verdict: tawk is DOM-drive -> a VendorConfig over the shared WidgetDriver (ADR-0007)

`Tawk_API` exposes NO method that transmits a visitor message. The full surface (captured live):
maximize, minimize, toggle, popup, showWidget, hideWidget, toggleVisibility, getStatus, getWindowType,
isChatMaximized/Minimized/Hidden/Ongoing, isVisitorEngaged, endChat, setAttributes, addEvent, addTags,
removeTags, customStyle, login, logout, switchWidget, start, shutdown, onLoad/onBeforeLoad, and event
CALLBACKS (onChatMessageVisitor, onChatMessageAgent, onPrechatSubmit, onOfflineSubmit, ...). The closest,
`onChatMessageVisitor`, is a READ-ONLY listener that fires AFTER the visitor sends - not a sender. So
unlike Gorgias/Crisp (clean JS send API), tawk must be driven through the DOM: open, type into the
composer, press Enter. It belongs on WidgetDriver, not as a hand-written API-send class. (Adversarially
verified: a second agent re-read the whole JS API and found no send method.)

## Embed model: a same-origin about:srcdoc iframe (NOT cross-origin, NOT inline/shadow)

This is the one place the docs misled (the docs agent inferred a cross-origin embed.tawk.to iframe). Live
truth: the v4 widget renders its chat panel inside an **`about:srcdoc` iframe** (same-origin, populated by
JS), with sibling `about:blank` iframes for the launcher bubble ("Online") and a spare. Consequences:
- `getWindowType()` returns "inline" and `page.frames` shows NO frame whose URL contains "tawk" - the panel
  frame's URL is `about:srcdoc`. A URL/title/name filter finds nothing (the iframe ids are random+timestamp,
  e.g. `hns6rg4n57ss1782563241773`, and titles are null).
- A main-document query (even shadow-piercing) finds nothing tawk - the widget DOM is in the iframe document.
- BUT the iframe is same-origin, so Playwright drives it directly via frame access. **Resolve the frame by
  CONTENT**: the frame where `frame.locator('.tawk-chatinput-editor').count() > 0`. This is the iframe
  capability WidgetDriver needs - frame-by-content-marker, not frame_locator(stable-selector).

## The visitor flow (proven up to the send)

1. `goto(url)`; wait for `window.Tawk_API && window.Tawk_API.maximize` (function present). getStatus()=="online" on all 3.
2. Open: `window.Tawk_API.maximize()` (page-level JS; works).
3. Resolve the tawk panel frame by the `.tawk-chatinput-editor` marker.
4. Home screen shows: "We are live and ready to chat with you now. Say something to start a live chat." +
   a **"New Conversation"** entry + Home/Messages bottom-nav. Click **"New Conversation"** (worked on both
   default stores) -> message view.
5. Composer = **`textarea.tawk-chatinput-editor`** (TWO match in DOM; pick the VISIBLE one - the first is
   hidden). Placeholder "Type here and press enter.." / "Write a reply..". Send = **Enter** (the placeholder
   says so); fallback send control = `i.tawk-icon-send` / `.tawk-chatinput-button`.

## Email gate / reply-capture: the key risk

Both probed stores showed **NO pre-chat email form** (`email_fields: []`) - the composer is immediately
usable, so there is nowhere to leave our reply address by default. This is the project-wide reply-capture
problem, sharper for tawk than Tidio (Tidio at least gave us a pre-chat email field to fill). Options, all
UNPROVEN until a test store:
- **add_init_script visitor injection (most promising):** the docs say `Tawk_API.visitor = {name, email}` set
  BEFORE the loader downloads identifies the visitor. We control navigation, so we can inject it with
  Playwright `add_init_script` before `goto`, leaving our reply email even with no pre-chat form. Needs a
  test store to confirm an operator reply then emails back to that address.
- Pre-chat / offline form when a store has one enabled (configurable; absent on these 3).
- `setAttributes({email})` needs Secure Mode + HMAC hash for email -> not usable generically.

## Send-confirmation (needs a real send to finalize)

Two candidate honest-confirm signals, to verify on a test store (do NOT spam real stores):
- **`onChatMessageVisitor` callback (preferred):** inject before send -
  `Tawk_API.onChatMessageVisitor = m => (window.__twk_sent=window.__twk_sent||[]).push(m)` then poll
  `window.__twk_sent` for our token. Clean, like Tidio's wire frame but via the official callback.
- **Websocket frame:** tawk runs a socket.io ws to `wss://vsb<NN>.tawk.to/s/?...` (dynamic host). A visitor
  send should carry the text in a frame; token-match like Tidio. Backup if the callback proves unreliable.

## Loader-liveness gate (mirrors Tidio)

Live tawk store embeds `https://embed.tawk.to/<propertyId>/<widgetId>` (propertyId = 24-hex, widgetId =
alphanumeric, e.g. `/5a4e68f94b401e45400bdeaa/default` or `/686538b3e9265e190f81c03f/1iv5mb06s`). GET it:
200 = live, 401/403/404/410 = dead account, else retryable. Regex: `embed\.tawk\.to/[0-9a-fA-F]{16,}/[0-9A-Za-z]+`.
Pool reality: of 14 StoreLeads apparel stores tagged with tawk, only **3 (21%)** carried the direct loader
tag with a live 200; the other 11 inject via app-embed/GTM/deferred (no static tag) - the same static-gap
we saw with Tidio. So the gate + a fresh tech-filtered list are both needed for volume.

## Build implications (for the WidgetDriver extension + TAWK config)

- WidgetDriver gains optional **frame-by-content-marker** resolution: when `widget_frame_marker` is set, find
  the frame containing it and scope composer/entry/email/send to that frame instead of the page.
- Composer selection must pick the VISIBLE match (tawk has 2 `.tawk-chatinput-editor`).
- New **confirm_strategy** "callback_flag" (onChatMessageVisitor) - verify on test store; ws-token as backup.
- **email_strategy** likely "init_visitor" (add_init_script) rather than a pre-chat form - verify on test store.
- TAWK config (known): widget_frame_marker `.tawk-chatinput-editor`; open_js `Tawk_API.maximize()`;
  ready_predicate `window.Tawk_API && window.Tawk_API.maximize`; entry_labels ("New Conversation", ...);
  composer `textarea.tawk-chatinput-editor`; not_ready_detail `no_tawk_api`; loader gate as above.

## Verified end to end with a real send (allurepack.com, 2026-06-27)

The real TawkAdapter / WidgetDriver(TAWK) code (not the probe scripts) was run against the live stores:
it resolves the iframe, clicks the entry, and reaches a VISIBLE composer on both standard-widget stores.
Then a real HITL send delivered the FULL pitch into allurepack.com's Tawk chat - confirmed by screenshot
(the pitch posted in the thread, composer cleared) and by the ledger advancing to Pitched. The
production-path gate also passes the 3 live stores and fails app-embed stores with no direct loader.

Two things the real send taught us:
- **onChatMessageVisitor (registered post-load) did NOT fire**, so the first send reported a FALSE
  no_delivery_confirmation even though the message visibly sent. Confirm switched to **dom_echo**: our
  token appears in the rendered thread AND the composer has cleared (the composer-empty clause is what
  stops the un-sent token in the composer from false-confirming). Re-run reported "pitched - sent".
- A latent bug: the deliver-then-raise handler referenced `page`/`surface` which are unbound if the
  browser launch throws first (the launch failed once because the adapter defaults BROWSER_CHANNEL to
  "chrome"; the box has bundled chromium). Both are now initialised to None and guarded.

## Known limitation: the "help center" widget variant

mohifashion.com runs a CUSTOMISED widget whose Home is a "Need help? ... start a conversation" help-center
screen with no composer until deeper in. The shipped code resolves its frame (via the `.tawk-chat-panel`
root) and clicks the entry, but its composer appears via a different flow, so we do not reach it. Standard
widgets (the common case) work. This variant is a follow-up, not a blocker.

## Open (after delivery proven)

- The "help center" widget variant (mohifashion): resolves the frame + clicks the entry but routes the
  composer differently. Follow-up if that variant turns out to be common.
- Reply-capture (does a merchant reply ever reach us) stays the project-wide open question; for tawk the
  candidate path is add_init_script visitor-email injection, to be settled deliberately later - NOT via a
  trial test store (that approach already failed for Tidio).
