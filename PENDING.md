# Pending

## Model (2026-06-29): ONE-WAY delivery

We only need to DELIVER the pitch. It carries our website (mercwise.com) + booking link
(cal.com/nikhil1/30min), so an interested merchant contacts us. We do NOT capture inbound replies.
So: the **residential proxy is HELD**, the **Reply Watcher matcher fix is DROPPED**, and priority is
**breadth across the clean composer vendors** (no captcha, no proxy), with Shopify Inbox on the free
datacenter path as bonus volume.

## Grow the pool FIRST (2026-06-30) - pool is the capacity ceiling

Measured capacity now ~14.5k deliverable (~97% Shopify Inbox, free datacenter path, throttled). Each
store gets ONE pitch, so the POOL is the ceiling. Per-vendor pools + receipts:
`research/pool-and-capacity.md` (or memory `reference_chat_outreach_pool_and_capacity`).
- **The 8M "main file" (combined_domains.csv) is NOT a cheap pool.** It is domain+platform only (no
  chat tags); a fetch+detect feasibility test from Server #1 got 41% fetch / **1% chat-vendor density**
  (datacenter IP blocks + JS-injected widgets miss static fetch). Don't re-scan it; StoreLeads tags
  already did the JS-render detection.
- **Activate the tagged ~94k (the real near-term growth):**
  - ~~**Verify Gorgias** (+6,220)~~ **DONE 2026-06-30 - STRUCK.** The StoreLeads "Gorgias" tag is a
    HELPDESK/contact-forms platform tag, NOT the chat widget. 0/140 random qualified stores expose
    `window.GorgiasChat` (62% bridge-only = Gorgias email with chat OFF, 35% stale). The drivable
    Gorgias-CHAT pool is ~0%; the +6,220 was illusory. Adapter still hardened (migrated to
    ApiSendDriver, now confirms by dom_echo not optimistic "pitch_sent"); re-qualify any Gorgias list
    with `research/gorgias_chatlive.py` before pitching. `research/gorgias-chat-verification.md`.
  - **Untapped vendors - spiked 2026-06-30** (`research/widget-vendor-spike.md`):
    - **Olark SHIPPED** (verify-to-composer 70%) and **Zoho SalesIQ SHIPPED** (45%, lifted from 35%
      by broadening the composer selector to any textarea in Zoho's chat frame). Both in the engine +
      registered; per-vendor qualified lists extracted from `domains_export.csv`.
    - **Kustomer + Richpanel + Re:amaze = DROPPED 2026-06-30 (round 2).** A generic launcher-click
      spike did not unlock them: Richpanel 0/6, Kustomer 1/6 (a misclick), Re:amaze popup() opens no
      detectable menu frame headless. Globals are live (Richpanel/Kustomer) but no composer mounts in
      a headless browser. Only Olark + Zoho are headless-drivable among the untapped tags.
    - **Freshchat / Gladly / Freshdesk = DROP** - tags stale in the sample (globals absent); revisit
      only if a fresher tagged list shows them live.
    - Remaining Zoho ceiling: ~7/20 stores gate behind a pre-chat/offline form (no textarea surfaces)
      - not worth more spike.
  - Extract qualified (no-AI) per-vendor lists for the MAIN vendors (SI/Tidio/Zendesk/...) from
    `domains_export.csv` so all 94k is drivable for the consolidated send batch (still to do).
- **Depth beyond 94k = a richer StoreLeads export** (WITH technologies/installed_apps columns - the 8M
  file lacks them - and a mid-market revenue band). Nikhil pulls when back in StoreLeads.

## Next up (after pool growth)

- **Consolidated clean-vendor delivery batch (HITL, items 2+3 - APPROVED, not yet run).** One
  `batch_cli <list> --vendors tidio,tawk.to,zendesk,chatra,livechat,crisp --send` over a fresh
  multi-vendor list: detection routes per store, which fires the **owed first real sends** for Zendesk
  / Chatra / LiveChat AND delivers the new pitch at volume on the proven vendors (Tidio, Tawk). Needs:
  a fresh multi-vendor domain list, and confirm scale with Nikhil before firing (real outbound). Crisp
  is verify-to-composer proven; its first real send happens in this batch. Re:amaze excluded (deferred).
- **HelpScout send path** still owed: the "Ask" form is fill-email + Send + a thank-you-state confirm,
  not type+Enter+dom_echo. Intercom: `startConversation` transmit still unconfirmed.
- **Zendesk Classic Web Widget variant.** The config targets the dominant modern *messaging* widget;
  the legacy Classic widget (iframe#webWidget, `textarea[name="message"]` + name/email pre-chat) is a
  minority and unhandled. Build only if the live pool shows enough Classic stores to matter.

## Shopify Inbox (count leader ~49k) - delivery understood, verdict hardened

- **Adapter is double-send-safe (rebuilt 2026-06-29).** The 75-store run proved the real bottleneck is
  NOT captcha mechanics: the contact-form passive hCaptcha **silently rejects ~half the submissions
  from a datacenter IP** (committed-delivery decayed 67% -> 48% with cumulative volume, 0 visible
  challenges). The verdict now treats a clicked send as always-terminal and only retries when nothing
  posted (provably double-send-safe). 20 wrongly-burned stores were reset to Queued.
- **Residential proxy WIRED (ProxyBase) 2026-06-30** - no longer held. Confirmed residential+rotating,
  Chromium-auth OK, creds in a gitignored Server #1 `.env.proxy` (opt-in). Measured SI cost 0.97 MB/store
  images-blocked (33 GiB prepaid ~= 34k store-loads; full 73.5k = ~71 GB > balance, card attached - cap +
  image-block + monitor, never blanket-route). **NEXT (HITL): a small SI delivery A/B (proxy vs direct,
  images-blocked, ~15-20 stores) Nikhil fires** to measure whether residential lifts submit-acceptance
  above the 48-67% datacenter baseline. Prereq (autonomous): wire image/media blocking into the engine's
  proxy path. See `reference_proxybase_residential_proxy` (memory).
- **Still open:** widget-variant misses (`no_composer`/`no_launcher` selectors) - the only remaining
  adapter-robustness bucket, needs real-DOM evidence.

## Vendors built this session

- **Crisp - SHIPPED.** `window.$crisp`, open `chat:open`, composer in the page DOM, dom_echo,
  email=none. Verify-to-composer 6/18 (33% raw, ~60% of live; rest stale tags). 275 tagged stores.
- **Re:amaze - BUILT BUT DEFERRED (0/15).** `popup()` opens a MENU, not the composer; the composer is
  behind an entry click and the about:blank frame needs a menu-stage marker (the composer marker is
  absent at menu time). Own spike. 848 tagged stores. (research/crisp-reamaze-injection.md)

## Data / pool

- Apparel-Tidio list is aged (~70% dead accounts); the gate-liveness check filters dead accounts
  cheaply now. StoreLeads lists on Server #1: crisp_stores.txt (275), reamaze_stores.txt (848). Need a
  fresh multi-vendor list for the consolidated batch.

## Dropped / parked

- **Reply Watcher matcher fix - DROPPED** (one-way model; success = cal.com bookings, not inbox
  replies). The watcher still runs non-destructively but is off the critical path; it over-counts
  brand-domain marketing emails as "replies" (knesko.com was one). First REAL human reply did land
  (scoutdesignstudio.com, a decline) - the loop works, we just don't depend on it. [[feedback_never_mark_real_inbox_read]]
