# chat-outreach-engine

Pitches ecommerce brands inside their **own live chat widget**, offering to build them an AI
chatbot, and tracks replies through to a booked call. Volume grows by adding per-vendor
support, **never by switching to cold email** (ADR-0001).

See `CONTEXT.md` for the glossary, `docs/adr/` for decisions, `CHANGELOG.md` for what changed,
`PENDING.md` for what's open.

## Status (2026-06-27)

Engine works end-to-end. Tidio is the live vendor; delivery on modern (v4/Lyro) stores is
fixed, and the gate now filters dead/expired accounts over HTTP before spending a browser
launch. 61 tests green.

**The honest foundation, measured (random N=40, production path):** of the ~2,640 apparel-Tidio
pool, ~7.6% are actually deliverable (~200 live stores) - the rest are dead accounts whose
static tag lingers. So scale is a **breadth** problem (more vendors), not a speed problem.

## Where it's going

Generalize the Tidio adapter into a shared `WidgetDriver` + per-vendor `VendorConfig` so each
new vendor (Crisp next) is cheap and reskin-proof, then widen vendor coverage. The unsolved
question is **reply capture** - whether a merchant's reply reliably reaches our inbox (still
unproven; see `PENDING.md`).

## Stack

Python, `uv`, `pytest`, SQLite Ledger, Playwright. Heavy runs on Server #1 (not the Mac).
Built via the Spike/Plan/Build/Harden playbook. Tracker: GitHub issues on
nikhilthale22-oss/chat-outreach-engine (see `CLAUDE.md`).
