# chat-outreach-engine

Pitches ecommerce brands inside their **own live chat widget**, offering to build them an AI
chatbot, and tracks replies through to a booked call. Volume grows by adding per-vendor
support, **never by switching to cold email** (ADR-0001).

See `CONTEXT.md` for the glossary, `docs/adr/` for decisions, `CHANGELOG.md` for what changed,
`PENDING.md` for what's open.

## Status (2026-06-30)

**Model: ONE-WAY delivery, and the STORE is the unit - reach it through ANY door.** We only need to
DELIVER the pitch (it carries mercwise.com + cal.com/nikhil1/30min, so an interested merchant contacts
us; no reply capture). Two doors, equal, neither sidelined: the **chat widget** and the store's native
**contact form**. Per store: chat-first, form-fallback, one pitch (the Ledger enforces one). Success =
cal.com bookings. **Current focus: make money on the free channels first, then decide what to scale.**

Engine works end-to-end. DOM-drive vendors are configs over a shared `WidgetDriver` (ADR-0007); two get
their own class. **Real-send proven:** Tidio, Tawk, Shopify Inbox. **Verify-to-composer proven:** Zendesk
(5/5), LiveChat, Chatra, HelpScout, **Crisp** (33%), **Olark** (`window.olark`, page-DOM textarea, **70%** -
strongest), **Zoho SalesIQ** (about:blank-frame textarea, **45%**). **API-send:** Gorgias (now confirms by
dom_echo via ApiSendDriver), Intercom (wired). **Dropped (not headless-drivable):** Re:amaze, Richpanel,
Kustomer, Freshchat/Gladly/Freshdesk. 176 tests green.

**Gorgias struck from the pool:** the StoreLeads "Gorgias" tag is a HELPDESK/contact-forms tag, not the
chat widget - 0/140 random qualified stores expose `window.GorgiasChat` (re-qualify with
`research/gorgias_chatlive.py` before pitching). The "+6,220" was illusory.

**Contact form** (`adapters/shopify_contact_form.py`, the second door): the store's native Shopify form,
posts through their own site into their support inbox (sidesteps our email deliverability problem) and is
the door most likely to be READ (a chat bubble can sit unseen). BUT it is gated by an INTERACTIVE hCaptcha
that neither the proxy nor a headed browser beats (0/8); paid solver ruled out. So we deliver the
**captcha-free subset only (~6% of Shopify stores)** and skip the rest. It is the highest-quality, smallest
free slice.

**Shopify Inbox** (count leader): its PASSIVE hCaptcha **silently rejects ~half the submissions from a
datacenter IP** (softer than the contact form's). Verdict is double-send-safe. The **residential proxy is
wired** (ProxyBase, residential+rotating, opt-in via a gitignored Server #1 `.env.proxy`); SI cost ~0.97
MB/store images-blocked (33 GiB prepaid, card attached - cap + image-block, never blanket-route). NOTE:
the proxy lifts LOADING/reach, but does NOT beat Shopify's hCaptcha.

**Next: prove conversion (0 bookings so far).** A real HITL send batch on the free channels (SI + clean
vendors + captcha-free contact forms) to get the first booking, then decide what is worth scaling.

## Where it's going

Breadth: a new DOM-drive vendor is a `VendorConfig` over `WidgetDriver`. Next is one consolidated
clean-vendor `--send` batch with the new one-way pitch - it fires the owed first sends for
Zendesk/Chatra/LiveChat and delivers at volume on Tidio/Tawk/Crisp (see `PENDING.md`). The first real
human reply did land (a decline), proving the loop, but the one-way model no longer depends on it.

## Stack

Python, `uv`, `pytest`, SQLite Ledger, Playwright. Heavy runs on Server #1 (not the Mac).
Built via the Spike/Plan/Build/Harden playbook. Tracker: GitHub issues on
nikhilthale22-oss/chat-outreach-engine (see `CLAUDE.md`).
