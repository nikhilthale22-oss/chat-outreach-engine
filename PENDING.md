# Pending

## Next up (scale by breadth)

- **Slice 2 parity run (HITL).** WidgetDriver + VendorConfig is built and parity-checked offline (config-generated selectors/JS diffed byte-for-byte against the old Tidio literals; 82 tests green). Still owed: one live Tidio send through `WidgetDriver(TIDIO)` on talleyandtwine to confirm the lifted browser flow behaves identically. Nikhil runs the real send.
- **Slice 3: pluggable delivery confirmation** (wire_token default + request-body watch + dom_echo + none). `confirm_strategy` already exists on VendorConfig with `wire_token`/`none`; add the other confirmers.
- **Slice 4: Tawk as the second DOM-drive vendor - BUILT + DELIVERY PROVEN.** (Crisp was dropped: API-send like Gorgias and only ~145 stores, so it would not exercise WidgetDriver.) Tawk is a `VendorConfig` over WidgetDriver + a new frame-by-content-marker capability; a real send delivered the full pitch into allurepack.com (ledger -> Pitched), confirmed by `dom_echo`. Outstanding: (a) the "help center" widget variant (mohifashion) reaches the frame+entry but not the composer; (b) reply-capture for tawk (add_init_script visitor-email injection) is the project-wide open question, deliberately deferred.
- **Real online sends owed (verify-to-composer done, not send-proven):** LiveChat, Chatra, HelpScout, Intercom, and **Zendesk**. Each needs one real send against an ONLINE store, with a human in the loop, to prove transmit + confirm (like Tawk's allurepack send). HelpScout additionally needs its send path built (the "Ask" form is fill-email + Send + a thank-you-state confirm, not type+Enter+dom_echo). Intercom needs its `startConversation` transmit confirmed. Zendesk verified 5/5 to composer via `dry_run`; the send path is plain type+Enter+dom_echo, so the real send just needs a human in the loop.
- **Zendesk Classic Web Widget variant.** This session's config targets the dominant modern *messaging* widget. The legacy *Classic* widget (iframe#webWidget, `textarea[name="message"]` + a name/email pre-chat form) is a minority (Zendesk deprecated it) and is not yet handled - it needs a second config with `email_strategy="prechat_then_api"` and a webWidget frame marker. Build only if the live pool shows enough Classic stores to matter.
- **Shopify Inbox - BUILT + DELIVERY PROVEN (2026-06-29), the count leader (~49k).** Own-class `adapters/shopify_inbox.py`: open shadow DOM -> type -> Send -> First/Last/Email form -> Start chat -> dom_echo. The hCaptcha is invisible/passive (passes free). Real send delivered (brandingirons.com via the adapter). **Owed:** (a) ROUTING - the static detector misses the JS-injected widget, so the engine marks SI stores "no chat widget" before the adapter runs; needs a browser-layer detect pass OR a known-SI-list batch run (the adapter self-detects via `no_shopify_inbox`, so a known-list run works now). (b) invisible-hCaptcha pass-RATE at scale (only N≈2 so far) - measure across ~20 stores. (c) it leaves an email = the best shot at proving reply-capture.
- **Re:amaze (131, best reply-path) - DRIVABLE, deferral was wrong (re-probed 2026-06-29).** The SDK exposes `Shoutbox`/`ShoutboxInit` (the chat composer); `popup()` was the wrong verb. SDK loads lazily (slow-init like Zendesk). Build: wait for the SDK, call `Reamaze.Shoutbox()`, verify-to-composer, then a WidgetDriver config or own class.
- **Crisp - DRIVABLE, wrongly dropped (re-probed 2026-06-29).** `$crisp.push(['do','chat:open'])` reaches a visible composer (2/4 live); `do` verb present for `message:send`. Small pool (~40+) but a tiny config flips every Crisp store from Dead -> drivable.
- **False-belief retest backlog (from the 2026-06-29 audit).** Safe (no-send) suspects still to verify: Tidio app-embed/GTM "never loads" (likely slow-init), every `no_X` not-ready treated as terminal, `prechat_blocked_required_fields`=Dead (test if filling flushes), Gorgias headless init + helpdesk-vs-chat tag, has_ai static-label exclusion. Cross-project: CRM site-scrape "DEAD (reCAPTCHA)" and Meta Ad Library "dead" are the same datacenter-IP/passive-captcha trap. Full ledger in the audit result.

## Data / pool

- Apparel-Tidio list is aged (~70% dead accounts). Get a fresher StoreLeads scan and/or add verticals. The gate-liveness check now filters dead accounts cheaply, so a re-run is no longer wasteful.

## Open decisions (Nikhil)

- Run the Slice 2 parity send on talleyandtwine, then move to Slice 4 (Crisp) for the real breadth proof, or first re-run the now-efficient scale on the ~200 live apparel stores to bank pitches.

## Blocked / unproven

- **Reply capture unproven.** Only reply ever seen = a glamnetic Gorgias auto-CSAT (a bot). The reply-round-trip spike (#12) was abandoned (a trial Tidio account won't surface a localhost-widget conversation). ADR-0002's "every vendor emails the reply" stays unverified; a dashboard-poll fallback may be needed.
- **IMAP app password** for nikhilthale18@gmail.com not provided, so the Reply Watcher can't run automated.
