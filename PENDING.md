# Pending

## Next up (scale by breadth)

- **Slice 2 parity run (HITL).** WidgetDriver + VendorConfig is built and parity-checked offline (config-generated selectors/JS diffed byte-for-byte against the old Tidio literals; 82 tests green). Still owed: one live Tidio send through `WidgetDriver(TIDIO)` on talleyandtwine to confirm the lifted browser flow behaves identically. Nikhil runs the real send.
- **Slice 3: pluggable delivery confirmation** (wire_token default + request-body watch + dom_echo + none). `confirm_strategy` already exists on VendorConfig with `wire_token`/`none`; add the other confirmers.
- **Slice 4: Tawk as the second DOM-drive vendor - BUILT + DELIVERY PROVEN.** (Crisp was dropped: API-send like Gorgias and only ~145 stores, so it would not exercise WidgetDriver.) Tawk is a `VendorConfig` over WidgetDriver + a new frame-by-content-marker capability; a real send delivered the full pitch into allurepack.com (ledger -> Pitched), confirmed by `dom_echo`. Outstanding: (a) the "help center" widget variant (mohifashion) reaches the frame+entry but not the composer; (b) reply-capture for tawk (add_init_script visitor-email injection) is the project-wide open question, deliberately deferred.
- **Real online sends owed (verify-to-composer done, not send-proven):** LiveChat, Chatra, HelpScout, Intercom, and **Zendesk**. Each needs one real send against an ONLINE store, with a human in the loop, to prove transmit + confirm (like Tawk's allurepack send). HelpScout additionally needs its send path built (the "Ask" form is fill-email + Send + a thank-you-state confirm, not type+Enter+dom_echo). Intercom needs its `startConversation` transmit confirmed. Zendesk verified 5/5 to composer via `dry_run`; the send path is plain type+Enter+dom_echo, so the real send just needs a human in the loop.
- **Zendesk Classic Web Widget variant.** This session's config targets the dominant modern *messaging* widget. The legacy *Classic* widget (iframe#webWidget, `textarea[name="message"]` + a name/email pre-chat form) is a minority (Zendesk deprecated it) and is not yet handled - it needs a second config with `email_strategy="prechat_then_api"` and a webWidget frame marker. Build only if the live pool shows enough Classic stores to matter.
- **Re:amaze (131, best reply-path vendor) - DEFERRED.** `Reamaze.popup()` opened a help-center lightbox, not the chat shoutbox composer; SDK global loaded inconsistently. Needs a look at targeting the shoutbox widget.

## Data / pool

- Apparel-Tidio list is aged (~70% dead accounts). Get a fresher StoreLeads scan and/or add verticals. The gate-liveness check now filters dead accounts cheaply, so a re-run is no longer wasteful.

## Open decisions (Nikhil)

- Run the Slice 2 parity send on talleyandtwine, then move to Slice 4 (Crisp) for the real breadth proof, or first re-run the now-efficient scale on the ~200 live apparel stores to bank pitches.

## Blocked / unproven

- **Reply capture unproven.** Only reply ever seen = a glamnetic Gorgias auto-CSAT (a bot). The reply-round-trip spike (#12) was abandoned (a trial Tidio account won't surface a localhost-widget conversation). ADR-0002's "every vendor emails the reply" stays unverified; a dashboard-poll fallback may be needed.
- **IMAP app password** for nikhilthale18@gmail.com not provided, so the Reply Watcher can't run automated.
