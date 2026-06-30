# chat-outreach-engine

Pitches ecommerce brands inside their **own live chat widget**, offering to build them an AI
chatbot, and tracks replies through to a booked call. Volume grows by adding per-vendor
support, **never by switching to cold email** (ADR-0001).

See `CONTEXT.md` for the glossary, `docs/adr/` for decisions, `CHANGELOG.md` for what changed,
`PENDING.md` for what's open.

## Status (2026-06-30)

**Model: ONE-WAY delivery.** We only need to DELIVER the pitch; it carries our website (mercwise.com) +
booking link (cal.com/nikhil1/30min), so an interested merchant contacts us. We do NOT capture inbound
replies. Scale = **breadth across the clean composer vendors** + Shopify Inbox volume. Success = cal.com bookings.

Engine works end-to-end. DOM-drive vendors are configs over a shared `WidgetDriver` (ADR-0007); two get
their own class. **Real-send proven:** Tidio, Tawk, Shopify Inbox. **Verify-to-composer proven:** Zendesk
(5/5), LiveChat, Chatra, HelpScout, **Crisp** (33%), **Olark** (`window.olark`, page-DOM textarea, **70%** -
strongest), **Zoho SalesIQ** (about:blank-frame textarea, **45%**). **API-send:** Gorgias (now confirms by
dom_echo via ApiSendDriver), Intercom (wired). **Dropped (not headless-drivable):** Re:amaze, Richpanel,
Kustomer, Freshchat/Gladly/Freshdesk. 176 tests green.

**Gorgias struck from the pool:** the StoreLeads "Gorgias" tag is a HELPDESK/contact-forms tag, not the
chat widget - 0/140 random qualified stores expose `window.GorgiasChat` (re-qualify with
`research/gorgias_chatlive.py` before pitching). The "+6,220" was illusory.

**Shopify Inbox** (count leader): its passive hCaptcha **silently rejects ~half the submissions from a
datacenter IP**. The send verdict is provably double-send-safe. The **residential proxy is now wired and
confirmed** (ProxyBase, residential+rotating, opt-in via a gitignored Server #1 `.env.proxy`); measured SI
cost is ~0.97 MB/store images-blocked (33 GiB prepaid balance, **card attached - cap and image-block at
scale, never blanket-route the 73.5k**). Open: a HITL SI delivery A/B (proxy vs direct) to measure the lift.

## Where it's going

Breadth: a new DOM-drive vendor is a `VendorConfig` over `WidgetDriver`. Next is one consolidated
clean-vendor `--send` batch with the new one-way pitch - it fires the owed first sends for
Zendesk/Chatra/LiveChat and delivers at volume on Tidio/Tawk/Crisp (see `PENDING.md`). The first real
human reply did land (a decline), proving the loop, but the one-way model no longer depends on it.

## Stack

Python, `uv`, `pytest`, SQLite Ledger, Playwright. Heavy runs on Server #1 (not the Mac).
Built via the Spike/Plan/Build/Harden playbook. Tracker: GitHub issues on
nikhilthale22-oss/chat-outreach-engine (see `CLAUDE.md`).
