# Zendesk injection (live probe, 2026-06-28)

This overturns the earlier "defer Zendesk" call (research/vendor-landscape.md). Zendesk is the
biggest unbuilt vendor by raw count; the deferral blamed "unreliable headless / intermittent
composer / async messaging send". Live probing on Server #1 showed those were a slow-bundle race
plus a probe bug, not real flakiness. **Zendesk is DOM-drive and verified-to-composer 5/5.**

## Method

Random sample of 40 from the StoreLeads `installed_apps_names` grep for `zendesk|zopim` (broad pool
829, apparel 225 - both RAW grep counts, see "density" below). Probed headless (bundled chromium,
`BROWSER_CHANNEL=""`) on Server #1: load -> wait for `window.zE` -> read the snippet loader -> open
-> resolve the widget iframe -> look for a composer. Then a deep probe on the 9 live-snippet stores
with generous waits + a launcher click + frame-resolution by the iframe TITLE.

## What the probes found

**Two widget families, distinguishable by the widget iframe:**

- **Messaging (modern, dominant).** Conversation panel renders in a same-origin **srcdoc/blank
  iframe titled "Messaging window"** (no stable URL or id - Tawk-style). Composer is
  `textarea[placeholder="Type a message"]`. No pre-chat email gate; you type and send. Opened by
  `zE('messenger','open')`. 5 of the 6 composer-reachable stores.
- **Classic Web Widget (legacy, minority).** Panel is `iframe#webWidget` (title "Find more
  information here"); composer is `textarea[name="message"]` alongside a `name`+`email` pre-chat
  form. Opened by `zE('webWidget','open')`/`zE.activate()`. 1 store (thecupstore.com). Zendesk
  deprecated Classic, so new installs are messaging - this config targets messaging; classic is a
  future variant (different frame id, needs `email_strategy="prechat_then_api"`).

**Composer reachability (the 9 live-snippet stores):**

- composer reached: ashandemberoutdoors.com, www.dslrpros.com, www.slumberpod.com,
  www.blackradiancebeauty.com, anzzi.com (messaging) + thecupstore.com (classic) = **6/9**
- not reached: www.genexa.com (zE never initialised - inert/dead snippet), www.paradisegalleries.com
  (zE init, opened ok, but no panel rendered - account likely unprovisioned/agents off),
  pawfecthouse.com (actually **Freshworks**, not Zendesk, despite a stale zdassets snippet)

**Send mechanism = DOM, not API.** Both families render a real composer textarea, so the visitor
message is typed + Enter + dom_echo confirm (identical to Tawk/LiveChat). The async
`newConversation -> sendMessage` messaging API is NOT needed - it was the wrong abstraction the
deferral assumed.

## Why the original deferral was wrong

1. **Too-short post-open wait.** The messaging widget lazy-loads a heavy bundle on first open; the
   "Messaging window" iframe + composer appear several seconds later. A 3-4s wait missed them; a
   ~12-18s poll catches them every time.
2. **Frame-filter bug in the first probe.** It only scanned frames whose URL matched `zendesk`; the
   messaging panel has an EMPTY url (srcdoc), so it was skipped. Resolving the frame by the composer
   marker (content) finds it - the same `widget_frame_marker` mechanism Tawk uses.
3. **"Inert ~half" = the dead-account-lingering-tag problem,** identical to Tidio/Tawk. The snippet
   tag stays in the HTML after an account lapses (loader 40x's) and the static signature also matches
   stores that dropped Zendesk. The loader-liveness gate (GET `static.zdassets.com/ekr/snippet.js
   ?key=<uuid>`) filters them cheaply.

## Build

A `VendorConfig` (`ZENDESK`) over `WidgetDriver` (adapters/zendesk.py), DOM-drive:

- `ready_predicate = "window.zE"`, `not_ready_detail = "no_zendesk_api"`.
- `open_js` fires `messenger.open` + `webWidget.open` + `activate`, **each in its own try/catch**, so
  the verb that matches the store's family runs whatever family it is.
- `widget_frame_marker = composer_selector = "textarea[placeholder='Type a message' i]"` - resolves
  the "Messaging window" frame by content and scopes the composer to it.
- `email_strategy = "none"`, `confirm_strategy = "dom_echo"`.
- No new driver code was needed - Zendesk reuses Tawk's frame-by-marker + dom_echo. The seam paid off.

**Verify-to-composer: 5/5** messaging stores via the SHIPPED path
`WidgetDriver(ZENDESK).send(domain, pitch, email, dry_run=True)` -> `composer_reached`. `dry_run` was
added to `send()` for exactly this: reach the composer and return without typing or sending (transmits
nothing, so it is safe to run unattended). The shipped `open_js` alone surfaced the composer on all 5
- no launcher click required.

## Density (raw count over-counts, like Tidio)

Of 40 grep-matched stores, only **9 had a Zendesk snippet** in their live HTML and **8 initialised
`zE`** (~20-23%). So the raw 829 broad-pool count implies a real live-Zendesk pool of roughly ~165,
of which ~75% are messaging-family + composer-reachable. The loader-liveness gate + `no_zendesk_api`
do the winnowing cheaply, exactly as for Tidio/Tawk. State the live pool honestly, never the raw count.

## Owed

A real online HITL send (one messaging store, Nikhil runs) to prove transmit + dom_echo end-to-end,
like Tawk's allurepack send. Reply-capture remains the project-wide open question.
