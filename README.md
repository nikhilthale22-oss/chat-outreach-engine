# chat-outreach-engine

Pitches ecommerce brands inside their **own live chat widget**, offering to build them an AI
chatbot, and tracks replies through to a booked call. Volume grows by adding per-vendor
support, **never by switching to cold email** (ADR-0001).

See `CONTEXT.md` for the glossary, `docs/adr/` for decisions, `CHANGELOG.md` for what changed,
`PENDING.md` for what's open.

## Status (2026-06-27)

Engine works end-to-end. Vendors are configs over a shared `WidgetDriver` (ADR-0007). DOM-drive: Tidio
and **Tawk** (real-send proven), plus **LiveChat**, **Chatra**, **HelpScout** (built + verified to the
composer; real send owed). API-send (via `ApiSendDriver`): Gorgias, plus **Intercom** (wired, not yet
send-verified). The driver resolves iframe widgets by URL (livechatinc.com / chatra.io) or content marker
(Tawk's about:srcdoc, HelpScout's #beacon-container). 107 tests green. Deferred for a focused session:
Zendesk (654 stores, inconsistent headless) and Re:amaze (131, best reply-path) - see
`research/vendor-landscape.md`.

**The honest foundation, measured (random N=40, production path):** of the ~2,640 apparel-Tidio
pool, ~7.6% are actually deliverable (~200 live stores) - the rest are dead accounts whose
static tag lingers. So scale is a **breadth** problem (more vendors), not a speed problem.

## Where it's going

The breadth lever is built: a new DOM-drive vendor is a `VendorConfig` over `WidgetDriver`, and
the driver now handles same-origin iframe widgets (Tawk). Next: one real HITL send to finalise
Tawk delivery, then more vendors. The unsolved question remains **reply capture** - whether a
merchant's reply reliably reaches us (still unproven across thousands of sends; see `PENDING.md`).

## Stack

Python, `uv`, `pytest`, SQLite Ledger, Playwright. Heavy runs on Server #1 (not the Mac).
Built via the Spike/Plan/Build/Harden playbook. Tracker: GitHub issues on
nikhilthale22-oss/chat-outreach-engine (see `CLAUDE.md`).
