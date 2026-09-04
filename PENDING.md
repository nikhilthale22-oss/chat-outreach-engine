# Pending

## Direction (2026-07-18): Phase 3 spine + 5 vendors proven; pick the next lever

Phase 3 SPINE is built and 5 vendors are PROVEN live through the code on Server #1 (Tawk, Tidio, Chatra,
LiveChat, Help Scout = ~86% of the reachable pool; screenshots in `~/Claude Code/*-sent.png`). Built the
`contact_form` + `composer_intro` gate handlers; the 3 form vendors capture email so replies reach Nikhil's
Zoho. 219 green. Proof bar unchanged (`feedback_proven_only_when_user_sees_it`).

- **Open cleanup:** fold `batch.py` (volume runner) onto the `pipeline` unit; physically move the adapter
  files into `send/headed/`; remove Re:amaze from `route/registry.VENDOR_METHOD` (confirmed dead 0/15).
- **More vendors (lower coverage):** prove Crisp (~275), Zoho SalesIQ (~268), Olark (~218) the same way
  (immediate composer). LiveChat ONLINE-composer path still untested (only the offline form is proven; the
  online/offline state is time-of-day dependent).
- **Robustness:** occasional composer-click flake on odd stores (e.g. skullandbones) - add a fail-fast click.
- **Phase 4 Scale:** rotating residential IPs + queue + scheduler + ~12 parallel browsers + dashboard for
  volume. **Phase 5 Capture:** replies to Zoho + screenshots wired into the machine.
- **Check:** the 5 proof sends' replies in Nikhil's Zoho `nikhilmercwise@zohomail.in` (IMAP broken -> webmail).

## Direction (2026-07-16): chat-widget outreach via the DIRECT HTTP send (SUPERSEDES the build below)

Nikhil replanned the whole tool (CTO-grade). Chat is the MAIN channel; **stick to the chat widget for now, contact form later**. Always-on self-driving machine, non-technical operator, burnable identities + rotating IPs, own captcha solver later, target = ability to hit ~50k/day. The delivery mechanism is now the **reverse-engineered pure-HTTP Shopify Inbox send** (memory `reference_shopify_inbox_direct_send`), NOT browser automation.

- **PROOF GATE (Nikhil's, non-negotiable): he rejects terminal output as proof** (memory `feedback_proven_only_when_user_sees_it`). Nothing counts until he sees (1) a SCREENSHOT of our message in a real brand's live widget on their page, and (2) a REPLY landing in his Zoho `nikhilmercwise@zohomail.in` that he logs into himself. Arova (a store we own) = a "toy" to him.
- **NEXT: the proof batch.** Diversified 300 ready at `/tmp/chat300.csv`. Build screenshot-capture into a browser sender, fire a small live slice (10-15 real brands), show him the screenshots, then run the full 300 with a screenshot per store + replies to his Zoho. Produce an honest per-vendor scoreboard. **BLOCKED on his "go" to send to real brands.**
- Open: batch composition (full diversified 300 = honest per-vendor map with many blanks, vs weighted to SI/Tidio/Tawk = clean high delivery). Only SI has the fast method; 5 vendors have no adapter.
- Scripts on Server #1 `/root/` + Mac scratchpad (not committed). Zoho IMAP login broken (webmail only). Arova Inbox pending Shopify verification.
- The flows-payload (drop a bespoke flow-page link as the message content) still applies - it layers on AFTER the send is proven to Nikhil.

## Direction (2026-07-15): FLOWS-via-chat (SUPERSEDES the chatbot pitch below)

The channel now pitches **FLOWS, not chatbots** (Shopify's free AI assistant killed the standalone bot offer). Per brand: generate a bespoke flow-demo page (existing `conversion-engine`) and drop its link into the Shopify Inbox message. Canonical plan + risks: memory `project_flows_via_chat`.

- **Pool = 49,162 tagged Shopify-Inbox brands** (`~/Desktop/Storeleads/si_targets_49k.txt`). ~62% build a page, ~72% of those full colour+logo (N=40 measured). Nikhil approved the quality.
- **BUILD (spec'd, not coded):** (1) `pitches.py` -> two FLOWS templates with a `{link}` placeholder, A/B diverging in the first ~72 alnum chars (link near the END, so `_match_key` confirm stays stable); (2) NEW `flows_link.py` = `flows_slug()` + `slug_candidates()` (raw-domain AND www-stripped; ~9,299 www-domains diverge) + `resolve_live_link()` (HTTP-GET each, return first 200); (3) **HARD GATE: HTTP-200-check each brand's flow page right before pitching, skip on 404** (a dead demo burns the one-shot pool).
- **Runs on a NEW dedicated Hetzner box** (`mercwise-flows-01`, CPX31), isolated from Server #1; pages hosted on a SEPARATE domain (off mercwise.com, to protect the cold-email domain reputation). BLOCKED on a Hetzner API token.
- Still open: fix the ~50% pre-chat-form delivery loss (live-debug); pick the spare domain; decide pitch-all (~30k) vs colour+logo-only (~22k).

## Direction (2026-07-14): input-based VOLUME via the support box (Shopify Inbox)

SUPERSEDES the "make money first / prove conversion" framing below. Nikhil is now INPUT-based, not
outcome-based (memory `feedback_input_based_not_outcome_based`): drive volume so large the outcome is
inevitable; do NOT gate on bookings, do NOT build per-channel conversion attribution ("just want
meetings"). Keep only a minimal delivered-vs-blocked "input health" signal.
- **Channel = Shopify Inbox (the "support box"), NOT the contact form** (Nikhil: "we got support box
  fixed" - confirm whether that was a send-side code change).
- **Pool is bigger than the old ~14.5k.** That was the TAGGED Shopify-Inbox subset. Force Shopify Inbox
  (`--force-vendor shopify-inbox`, no detection) across the raw ~3.54M Shopify in the 8M
  `combined_domains.csv` for the volume play. Delivery on stores that actually run SI is ~a third to a
  half (measured); losses are ADAPTER ROBUSTNESS (widget absent on stale tags, strict confirm, form
  variants), NOT captcha - 0 captcha challenges in the 75-store run (corrected 2026-07-15). Bounded by how
  many raw stores actually run SI + reach, not the tagged pool. See `reference_chat_outreach_pool_and_capacity`.
- **First run: >=2,000 sends TODAY.** Plan: prep list -> dry-run -> warm-start 100 (watch
  delivered-vs-blocked) -> full 2k. Stop-safe; ledger prevents double-pitch. Nothing sent yet.
- **Open before firing:** (1) machine - Mac (best delivery, residential IP) vs Server #1 (datacenter);
  (2) point the pitch link OFF mercwise.com to a dedicated domain (brand insulation); (3) confirm what
  "support box fixed" means.
- **Reply inbox now = Zoho `nikhilmercwise@zohomail.in`** (off personal Gmail, verified live). Reply
  watcher still off the critical path, but the inbox is safe now.
- **Relaunch de-risking done:** 92-risk register + 64-fix launch plan produced (claude.ai artifacts). An
  ADR for this input-based / no-attribution / support-box direction is warranted once the 2k run settles it.
- **Moving to a FREE Oracle ARM server** (not provisioned; verify headless Chromium on ARM64 first -
  switch Playwright channel off "chrome").

## Model (2026-06-29, partly superseded by the 2026-07-14 direction above): ONE-WAY delivery

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

## MAKE MONEY FIRST (2026-06-30) - SUPERSEDED 2026-07-14 by input-based volume (see top). Kept for history.

Zero bookings so far. The open question is whether the pitch CONVERTS, not delivery breadth. So the
next real move is a **real send batch on the FREE channels** (HITL, Nikhil fires) to get the first
booking, then decide what to scale:
- Free channels: Shopify Inbox (~50% delivery, passive hCaptcha) + Olark/Zoho/Tidio/Tawk/Zendesk/
  Chatra/LiveChat/Crisp + captcha-free contact forms.
- **Contact form = second door, FREE SUBSET ONLY.** Built (`adapters/shopify_contact_form.py`), but
  most Shopify contact forms have an INTERACTIVE hCaptcha that neither proxy nor headed-browser beats
  (0/8); paid solver RULED OUT. Adapter skips captcha-gated stores, delivers the captcha-free subset.
- Routing rule: **chat-first, form-fallback, one pitch per store** (ledger enforces one). Wire the
  Injector so "no drivable chat" falls through to the contact form instead of Dead; reactivate the
  stores wrongly marked Dead (the 6,220 Gorgias helpdesk + other no-chat deads that have a form).
- Paid captcha solver / scaling contact forms = DEFERRED until the pitch is proven to make money.

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

- **Adapter is double-send-safe (rebuilt 2026-06-29).** CORRECTED 2026-07-15: the 75-store run recorded
  **0 captcha challenges** - captcha is NOT the bottleneck and there is NO "decays 67->48% from one IP"
  effect (that was a misread of `form_blocked`). The real losses are ADAPTER ROBUSTNESS: no_shopify_inbox
  32 (widget not present on stale-tag stores), submitted_unconfirmed 28 (confirm too strict, some likely
  delivered), form_blocked 14, launcher/send/composer variants 21. ~24-39 of 75 confirmed delivered. The
  verdict treats a clicked send as always-terminal and only retries when nothing posted (double-send-safe).
  20 wrongly-burned stores were reset to Queued.
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
  - UPDATE 2026-07-14: the gate inbox is now the dedicated Zoho box `nikhilmercwise@zohomail.in`
    (off personal Gmail), verified live. Env-driven via `.env.server`. See `reference_chat_outreach_reply_inbox`.
