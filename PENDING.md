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
  - **Verify Gorgias** (+6,220) - already tagged AND wired (ApiSendDriver), just never delivery-
    confirmed, so those 6.2k are currently unusable. One verification send flips them on. Biggest
    pool-per-effort win after SI.
  - **Build the untapped drivable+qualified vendors** (~2.5k): Richpanel 578, Freshchat 528, Freshdesk
    447, Zoho SalesIQ 268, Kustomer 245, Olark 218, Gladly 196 - spike -> VendorConfig -> verify-to-
    composer, same as Crisp. (Exclude already-AI tags: ChatBot, Gobot, ManyChat, Drift.)
  - Extract qualified (no-AI) per-vendor lists from `domains_export.csv` so all 94k is drivable.
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
- **SI scaling is on the FREE datacenter path only** (proxy HELD). Revisit a residential proxy ONLY if
  the clean vendors are tapped out and SI count becomes the binding constraint; an A/B (needs proxy
  creds) would confirm whether IP reputation is the lever before any spend.
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
