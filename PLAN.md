# 50k/day sending machine - PLAN

> One machine. Same steps on every store. Per-vendor "cards" fill in the *how*.
> Goal: reach up to ~50,000 ecommerce brands/day inside their own chat widget, unattended.

## The pipeline (one unit, runs on any store)

A domain goes in the left; a delivered message plus any captured reply comes out the
right, with nobody babysitting. Same steps every time. Only the per-vendor detail changes.

| Phase | Folder | What it does |
|-------|--------|--------------|
| 0 Input | (feed) | Domains from the 8M Shopify+Woo DB |
| 1 Detect | `detect/` | Which chat vendor + AI-bot vs human inbox (or "no chat") |
| 2 Route | `route/` | Vendor -> which send method (the "card") |
| 3 Send | `send/api/`, `send/headed/`, `send/form/` | Deliver via the routed method |
| 4 Scale | `scale/` | Rotating IPs, token factory, queue, scheduler, burnable identities |
| 5 Capture + Prove | `capture/` | Replies -> Zoho + screenshots/receipts |
| guardrail | `ledger/` | Never message the same store twice |

## The three send methods (every vendor is exactly one)

1. **api**: browserless HTTP. DROPPED for now (ADR-0008): 0 api vendors proven end to end - Gorgias chat is off on ~all tagged stores (0/140), Intercom is wired-only + AI-fronted, Shopify Inbox is now sign-in GATED. `send/api/` is parked, not wired.
2. **headed**: drive a real browser. Works, slow, needs a clean IP. Tidio, Tawk, Crisp, Zendesk, LiveChat, Chatra, HelpScout, Olark, Zoho SalesIQ, Re:amaze.
3. **none-yet**: no working path today. Set aside, never crashed. Drift, Kustomer, Freshchat, Gobot, Richpanel, ...

The machine always *runs* on any store; it only *delivers* where a card exists. New card = wider reach, no change to the machine.

## Migration map (existing code -> new home)

- `detect/`: `detect.py`, `signatures.py`  (move during Phase 1)
- `route/`: NEW (today the choice is buried in `batch.py` assessors)
- `send/api/`: `adapters/shopify_inbox.py`, `api_send_driver.py`, `adapters/gorgias.py`, `adapters/intercom.py`
- `send/headed/`: `widget_driver.py`, `injector.py`, `adapters/{tidio,tawk,crisp,chatra,livechat,helpscout,olark,zendesk,zoho_salesiq,reamaze}.py`
- `send/form/`: `adapters/shopify_contact_form.py`  (deferred, parked)
- `scale/`: `proxy.py` + NEW (token factory, queue, scheduler, IP pool, identities)
- `ledger/`: `ledger.py`  (move during ledger step)
- `capture/`: `reply_watcher.py`, `reply_watcher_cli.py` + NEW (screenshot/receipt proof)
- `ops/`: `cli.py`, `batch_cli.py` + NEW (dashboard)
- orchestrator: `batch.py` (walks detect -> route -> send), stays near the top

## Rules of engagement

- **Gated = skip.** The goal is pure volume, never fight a locked door. If a store needs sign-in, an
  unsolvable captcha, or required fields we cannot fill, mark it skipped and move on. Shopify Inbox +
  shopify-agent are currently gated (buyer sign-in) -> skip. Reachable = ungated human vendors + captcha-free forms.
- **All-headed (ADR-0008).** API send is dropped (0 vendors proven); the only active method is `headed`
  (drive the real widget). The registry is proven-only: a vendor is added only after it delivers live.
- Reshape moves code phase-by-phase. All 185 tests stay green at every step. No big-bang move.
- **Proof gate:** nothing is "proven" until Nikhil sees it, a screenshot on a real brand's own page plus a reply in his Zoho. Terminal 201s are not proof.
- Hard-to-reverse decisions go in `docs/adr/`. This file is the map, not a decision log.
- Package stays importable as `chat_outreach_engine` (repo folder is `50k-day-sending-machine`); renaming the package is a later, optional big-bang we are not doing now.

## Status

- [x] Repo renamed, phase skeleton created
- [x] PLAN locked, tests green (204)
- [x] Phase 1 Detect - detect/ package, human/ai/hybrid classifier, Shopify AI-agent detection, 12 tests
- [x] Phase 2 Route - registry + router, gated=skip (Shopify skipped), 7 tests, 211 green
- [~] Phase 3 Send - SPINE DONE + 5 VENDORS PROVEN LIVE THROUGH THE CODE. `pipeline.py` = the
  one-unit detect->route->send (`Pipeline.run_one`); `send/headed/` canonical adapter registry;
  `route/registry` all-headed (gorgias/intercom dropped, ADR-0008); 219 green. **PROVEN 2026-07-17/18,
  headless on Server #1, screenshot + code-confirm (`~/Claude Code/*-sent.png`):** Tawk
  (leatherglovesonline, dom_echo), Tidio (ourosjewels, wire_token+email gate), Help Scout (inkopious,
  contact_form), LiveChat (stephaniegottlieb offline, contact_form), Chatra (norwegian-wool +
  gembreakfast, composer_intro) = ~86% of the reachable pool. Built the `contact_form` + `composer_intro`
  gate handlers in `widget_driver` (fill name/email/subject/message + submit + honest confirm); the 3 form
  vendors CAPTURE email -> a real Zoho reply path. Fixed: typing self-heal (`fill()`), composer-detection
  retry (slow Beacon), Server #1 browser 1208 reinstall.
  REMAINING: fold `batch.py` onto the unit; move adapter files into `send/`; prove Crisp/Olark/Zoho;
  LiveChat online-composer path untested; occasional composer-click flake; remove dead Re:amaze from registry.
- [ ] Phase 4 Scale
- [ ] Phase 5 Capture + Prove
