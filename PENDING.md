# Pending

## Next up (scale by breadth)

- **Slice 2: generalize the adapter** into a shared `WidgetDriver` + per-vendor `VendorConfig`, prove byte-for-byte parity with the current Tidio adapter on a known-good store (talleyandtwine), then retire the hand-written class. New ADR: "vendors are generated from a config + shared driver, not hand-written" (reconcile the CONTEXT "one Adapter per vendor" line).
- **Slice 3: pluggable delivery confirmation** (ws_frame default + request-body watch + dom_echo + none).
- **Slice 4: submit_strategy / email_attach / iframe support**, proven by standing up a second vendor (Crisp) end to end.

## Data / pool

- Apparel-Tidio list is aged (~70% dead accounts). Get a fresher StoreLeads scan and/or add verticals. The gate-liveness check now filters dead accounts cheaply, so a re-run is no longer wasteful.

## Open decisions (Nikhil)

- Push the local gate-liveness + ADR-0005 commits (Slice 1 already pushed).
- Re-run the now-efficient scale on the ~200 live apparel stores to bank pitches, or go straight to Slice 2.

## Blocked / unproven

- **Reply capture unproven.** Only reply ever seen = a glamnetic Gorgias auto-CSAT (a bot). The reply-round-trip spike (#12) was abandoned (a trial Tidio account won't surface a localhost-widget conversation). ADR-0002's "every vendor emails the reply" stays unverified; a dashboard-poll fallback may be needed.
- **IMAP app password** for nikhilthale18@gmail.com not provided, so the Reply Watcher can't run automated.
