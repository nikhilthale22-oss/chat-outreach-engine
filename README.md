# chat-outreach-engine

Pitches ecommerce brands inside their **own live chat widget**, offering to build them an AI
chatbot, and tracks replies through to a booked call. Volume grows by adding per-vendor
support, **never by switching to cold email** (ADR-0001).

See `CONTEXT.md` for the glossary, `docs/adr/` for decisions, `CHANGELOG.md` for what changed,
`PENDING.md` for what's open.

## Status (2026-06-29)

Engine works end-to-end. DOM-drive vendors are configs over a shared `WidgetDriver` (ADR-0007); two get
their own class. **Real-send proven:** Tidio, Tawk, and **Shopify Inbox** - the count leader (~49k), its
own class, unlocked 2026-06-29 (the long-standing "CAPTCHA-walled" verdict was wrong; the form's hCaptcha
is invisible/passive and passes free - real delivery on brandingirons.com). **Verified to composer, real
send owed:** Zendesk (the biggest live-chat vendor, 5/5), LiveChat, Chatra, HelpScout. **API-send (via
`ApiSendDriver`):** Gorgias, Intercom (wired, not send-verified). **Drivable, build next (deferrals
overturned):** Re:amaze (has a `Shoutbox` API), Crisp (`$crisp` reaches a composer). 126 tests green.

**A false-belief audit (2026-06-29) found that >half our "blocked/parked/dead" beliefs were never tested**
(11 PROVEN / 34 SUSPECT / 7 STALE / 11 MEASURED) - four vendors had been written off on untested
assumptions (Shopify Inbox, Zendesk, Re:amaze, Crisp), all now recovered. Lesson recorded: a gate being
present is not a gate being enforced - test the actual submission. See `research/` + the audit ledger.

Known gap: Shopify Inbox is JS-injected so the static detector misses it; auto-routing needs a
browser-layer detect pass (the adapter self-detects, so a known-SI-list run works now).

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
