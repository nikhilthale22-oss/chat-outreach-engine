# Pending

## Next up (scale by breadth)

- **Slice 2 parity run (HITL).** WidgetDriver + VendorConfig is built and parity-checked offline (config-generated selectors/JS diffed byte-for-byte against the old Tidio literals; 82 tests green). Still owed: one live Tidio send through `WidgetDriver(TIDIO)` on talleyandtwine to confirm the lifted browser flow behaves identically. Nikhil runs the real send.
- **Slice 3: pluggable delivery confirmation** (wire_token default + request-body watch + dom_echo + none). `confirm_strategy` already exists on VendorConfig with `wire_token`/`none`; add the other confirmers.
- **Slice 4: Tawk as the second DOM-drive vendor - BUILT + DELIVERY PROVEN.** (Crisp was dropped: API-send like Gorgias and only ~145 stores, so it would not exercise WidgetDriver.) Tawk is a `VendorConfig` over WidgetDriver + a new frame-by-content-marker capability; a real send delivered the full pitch into allurepack.com (ledger -> Pitched), confirmed by `dom_echo`. Outstanding: (a) the "help center" widget variant (mohifashion) reaches the frame+entry but not the composer; (b) reply-capture for tawk (add_init_script visitor-email injection) is the project-wide open question, deliberately deferred.
- **LiveChat + Chatra: built + verified to composer; real online send still owed.** Both probed OFFLINE; need one real send each against an ONLINE store to prove the live composer + Enter + dom_echo path (like Tawk's allurepack).
- **Re:amaze (44 stores, DOM-drive, requires name+email = reply path).** Best reply-capture vendor. Re-probe its open (the `Reamaze` SDK global hadn't initialised on the first probe; try `Reamaze.reload()` + longer wait), then config it.
- **HelpScout (11), and online-store probes** for the offline-probed vendors.
- **DECISION - the two biggest unbuilt vendors are API-send.** Zendesk (174) and Intercom (32) transmit via JS (`zE('messenger','sendMessage')` / `Intercom('startConversation')`), not the DOM. That is the single largest remaining reach but a different build: a small Gorgias-style ApiSendAdapter (open -> newConversation/sendMessage -> confirm via the API callback). Worth doing - needs a go-ahead since it is a new mechanism. See `research/vendor-landscape.md`.

## Data / pool

- Apparel-Tidio list is aged (~70% dead accounts). Get a fresher StoreLeads scan and/or add verticals. The gate-liveness check now filters dead accounts cheaply, so a re-run is no longer wasteful.

## Open decisions (Nikhil)

- Run the Slice 2 parity send on talleyandtwine, then move to Slice 4 (Crisp) for the real breadth proof, or first re-run the now-efficient scale on the ~200 live apparel stores to bank pitches.

## Blocked / unproven

- **Reply capture unproven.** Only reply ever seen = a glamnetic Gorgias auto-CSAT (a bot). The reply-round-trip spike (#12) was abandoned (a trial Tidio account won't surface a localhost-widget conversation). ADR-0002's "every vendor emails the reply" stays unverified; a dashboard-poll fallback may be needed.
- **IMAP app password** for nikhilthale18@gmail.com not provided, so the Reply Watcher can't run automated.
