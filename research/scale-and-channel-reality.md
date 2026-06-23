# Research: scale + channel reality (harvested 2026-06-22)

Output of the Phase-0 research-interrupt. Numbers from local files (cited).

## Throughput is NOT the constraint
Injector (`send_no_ai.py`) is ~70s/brand sequential -> ~50/hour, ~1,200/day per worker,
and parallelizes trivially across browser workers. Speed never binds.

## The real constraint = how many brands we can inject into (vendor coverage)
- US Gorgias stores total: 10,738 (`us_gorgias_ranked.csv`)
- Gorgias with AI on (skip): 615 (`gorgias_ai_active.csv`)
- Gorgias, no AI (current target pool): 124 (`gorgias_no_ai.csv`); fresh ~120
- So the Gorgias-only channel maxes near ~1,800 even after classifying the rest.

The lever is VENDOR COVERAGE. `chatdetect` detects 62 vendors; we inject into 1.
Adding adapters for the other live-chat vendors is what grows the reachable universe
from ~10k stores to hundreds of thousands. See research/vendor-universe.md.

## Cold email: rejected (see ADR-0001)
Cold email was evaluated and rejected as a channel. Not revisited. The volume strategy is
vendor coverage on the chat channel, full stop.

## Open research item
Exact per-vendor store counts (Shopify Inbox / Tidio / Tawk / Crisp / Intercom / Zendesk
/ LiveChat) to prioritize which adapter to build first. To be pulled from scan data +
the Server #1 scanner.
