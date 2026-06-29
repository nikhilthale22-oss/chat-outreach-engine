# chat-outreach-engine

Pitches ecommerce brands inside their **own live chat widget**, offering to build them an AI
chatbot, and tracks replies through to a booked call. Volume grows by adding per-vendor
support, **never by switching to cold email** (ADR-0001).

See `CONTEXT.md` for the glossary, `docs/adr/` for decisions, `CHANGELOG.md` for what changed,
`PENDING.md` for what's open.

## Status (2026-06-29)

**Model: ONE-WAY delivery.** We only need to DELIVER the pitch; it carries our website (mercwise.com) +
booking link (cal.com/nikhil1/30min), so an interested merchant contacts us. We do NOT capture inbound
replies. So scale = **breadth across the clean composer vendors** (no captcha, no proxy); the residential
proxy is held and the reply-watcher matcher is off the critical path. Success = cal.com bookings.

Engine works end-to-end. DOM-drive vendors are configs over a shared `WidgetDriver` (ADR-0007); two get
their own class. **Real-send proven:** Tidio, Tawk, Shopify Inbox. **Verify-to-composer proven:** Zendesk
(5/5), LiveChat, Chatra, HelpScout, **Crisp** (`$crisp` chat:open, page-DOM composer, 6/18). **API-send:**
Gorgias, Intercom (wired). **Deferred:** Re:amaze (built but 0/15 - `popup()` opens a menu, composer behind
an entry click, own spike), and the Shopify Inbox residential proxy. 156 tests green.

Shopify Inbox (count leader ~49k) is delivery-understood: its passive hCaptcha **silently rejects ~half
the submissions from a datacenter IP** (not a visible challenge). The send verdict is now provably
double-send-safe (a clicked send is always terminal; only a never-clicked-still-gated send retries). SI
rides the free datacenter path as bonus volume.

## Where it's going

Breadth: a new DOM-drive vendor is a `VendorConfig` over `WidgetDriver`. Next is one consolidated
clean-vendor `--send` batch with the new one-way pitch - it fires the owed first sends for
Zendesk/Chatra/LiveChat and delivers at volume on Tidio/Tawk/Crisp (see `PENDING.md`). The first real
human reply did land (a decline), proving the loop, but the one-way model no longer depends on it.

## Stack

Python, `uv`, `pytest`, SQLite Ledger, Playwright. Heavy runs on Server #1 (not the Mac).
Built via the Spike/Plan/Build/Harden playbook. Tracker: GitHub issues on
nikhilthale22-oss/chat-outreach-engine (see `CLAUDE.md`).
