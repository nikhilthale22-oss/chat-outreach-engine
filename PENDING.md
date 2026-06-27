# Pending

## Next up (scale by breadth)

- **Slice 2 parity run (HITL).** WidgetDriver + VendorConfig is built and parity-checked offline (config-generated selectors/JS diffed byte-for-byte against the old Tidio literals; 82 tests green). Still owed: one live Tidio send through `WidgetDriver(TIDIO)` on talleyandtwine to confirm the lifted browser flow behaves identically. Nikhil runs the real send.
- **Slice 3: pluggable delivery confirmation** (wire_token default + request-body watch + dom_echo + none). `confirm_strategy` already exists on VendorConfig with `wire_token`/`none`; add the other confirmers.
- **Slice 4: stand up a second vendor (Crisp) end to end** as a `VendorConfig` (the real proof the breadth lever works with zero new flow code). May need a `postsend_form` email strategy and iframe support; add to the driver as Crisp demands them, test-first.

## Data / pool

- Apparel-Tidio list is aged (~70% dead accounts). Get a fresher StoreLeads scan and/or add verticals. The gate-liveness check now filters dead accounts cheaply, so a re-run is no longer wasteful.

## Open decisions (Nikhil)

- Run the Slice 2 parity send on talleyandtwine, then move to Slice 4 (Crisp) for the real breadth proof, or first re-run the now-efficient scale on the ~200 live apparel stores to bank pitches.

## Blocked / unproven

- **Reply capture unproven.** Only reply ever seen = a glamnetic Gorgias auto-CSAT (a bot). The reply-round-trip spike (#12) was abandoned (a trial Tidio account won't surface a localhost-widget conversation). ADR-0002's "every vendor emails the reply" stays unverified; a dashboard-poll fallback may be needed.
- **IMAP app password** for nikhilthale18@gmail.com not provided, so the Reply Watcher can't run automated.
