# Status log (historical)

The dated status entries that used to sit at the top of README.md, newest first. Moved here 2026-09-04 so the README could become a newcomer's guide. Nothing below is current; it is the record of how the engine got here.

## Status (2026-07-18)

**Phase 3 Send: the machine delivers, and it's proven live through the code.** `pipeline.py` is the
one-unit `detect -> route -> send` (`Pipeline.run_one`); `send/headed/` is the canonical adapter registry;
the router is all-headed. **5 vendors proven live, headless on Server #1, with screenshots + code
confirmation** (`~/Claude Code/*-sent.png`): **Tawk, Tidio, Chatra, LiveChat, Help Scout** = ~86% of the
reachable pool. Built a `contact_form` + `composer_intro` capability for the form-gated vendors, and those
three **capture the email so replies reach Nikhil's Zoho** (proof criterion 2, finally reachable). 219 green.
Next: fold `batch.py` onto the unit, prove the smaller vendors (Crisp/Olark/Zoho), then Phase 4 scale.

## Status (2026-07-17)

**Renamed + reshaped into a phase pipeline, plus a hard reality check.** The tool is now
`50k-day-sending-machine`, reshaped into `detect/ route/ send/ scale/ capture/ ops/` (PLAN.md). **First
real delivery proof landed:** Nikhil sent a pitch into Emerald Fine Jewelry's live Tawk chat by hand
(screenshot; Zoho reply pending). **Shopify Inbox is now sign-in GATED** (13/13 stores
`require_buyer_shop_sign_in=True`), so the 2026-07-16 browserless crack is dead. Strategy locked
(ADR-0008): **gated = skip, pure volume, drop the API path, all-headed** (0 API vendors proven; the only
real path is browser-driving the human live-chat widgets). **Phase 1 Detect + Phase 2 Route built and
tested, 211 green**, validated on real stores (human -> send, gated Shopify -> skip). Next: size the
reachable pool from the 8M DB, then Phase 3 Send (prove one headed vendor end to end through the code).

## Status (2026-07-16)

**Shopify Inbox delivery reverse-engineered into a browserless pure-HTTP send** (memory `reference_shopify_inbox_direct_send`): grab the store's `data-external-identifier` from its homepage, mint an invisible-hCaptcha token standalone (sitekey cc6e6e86, ~1.6s, no solver, origin+shop-agnostic), `POST create-conversation` -> 201. Storefronts block datacenter IPs (harvest needs a good IP) but the send backend does not. Architecture = token-factory + HTTP-sender-pool = 50k/day on one box. **CRITICAL: all verified in terminal only; Nikhil rejects terminal as proof** (memory `feedback_proven_only_when_user_sees_it`) and wants a real-brand batch with SCREENSHOTS + replies to his Zoho. Full replan: chat-widget only for now (contact form = the universal door but deferred), always-on machine, burnable identities + rotating IPs, own captcha solver later. Diversified 300 ready (`/tmp/chat300.csv`). **Next: the proof batch, BLOCKED on his GO to send to real brands.** See `PENDING.md`.

## Status (2026-07-15, pt2)

**PIVOT: the channel now pitches FLOWS, not chatbots** (Shopify's free AI assistant commoditized the standalone bot). Per brand we generate a bespoke flow-demo page (the existing `conversion-engine`) and inject its link into the Shopify Inbox message. Pool = **49,162 tagged SI brands**; ~62% build a page (72% full colour+logo). Shipped **retry-on-429** (a rate-limited store no longer false-Deads; 192 tests green). Measured raw SI density = **~1.3%** so the raw-millions play is not a frontier and a **proxy is ruled out** (free-direct drains the finite tagged pool). Next: build the bridge (per-brand flows pitch + a live-page HTTP-200 guard) on a **new dedicated Hetzner box**, isolated from Server #1 (a workflow agent wiped Server #1's live flow pages this session; restored). Blocked on a Hetzner API token. See `PENDING.md` + memory `project_flows_via_chat`.

## Status (2026-07-15)

**Evidence audit + two retractions.** Under a "prove every friction" challenge, we re-verified against the
real Server #1 ledgers and a live reach test. RETRACTED as unsupported: the "passive hCaptcha silently
rejects ~half / delivery decays 67->48% from one IP" story (the 75-store run had **0 captcha challenges**;
losses are adapter robustness) and the "per-box throughput is a constraint" claim (throughput never binds).
CONFIRMED with receipts: poor reach from a single datacenter IP (live 5% burst / ~41% paced), a flaky proxy
(1/3 tries 502), the proxy cannot carry a send (ADR-0006), pitch links still on mercwise.com, and the
`channel="chrome"` default that will fail on Oracle ARM. Net: the real, proven friction is the **single
send-IP** problem (reach + no proxy-for-sends). Open decision: accept single-IP decay and push raw volume,
or provision multiple send IPs. Next: brainstorm proven fixes for the confirmed issues.

## Status (2026-07-14)

**Relaunch prep + strategic pivot to input-based VOLUME.** The reply/gate inbox is now a free,
disposable Zoho box (`nikhilmercwise@zohomail.in`, off Nikhil's personal Gmail, verified live);
config is env-driven for the move to a FREE Oracle Cloud ARM server (not provisioned yet). Direction
is now **input-based, not outcome-based**: drive volume, do NOT gate on bookings or build per-channel
attribution. Channel = **Shopify Inbox (the "support box"), not the contact form**; the ~14.5k figure
was only the tagged SI subset, so the volume play is forcing Shopify Inbox across the raw ~3.54M
Shopify in the 8M file. A 92-risk pre-launch register + a 64-fix launch plan exist (claude.ai
artifacts). **Next: a >=2,000-send run (prep -> dry-run -> warm-start 100 -> full 2k), pending the
machine choice (Mac vs Server #1).** See `PENDING.md` for the live direction. 185 tests green.

## Status (2026-06-30, prior)

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

**Shopify Inbox** (count leader): the 75-store run DISPROVED the "captcha challenges at velocity" fear -
**0 captcha challenges** - and delivery losses are ADAPTER ROBUSTNESS (widget not actually present on
stale-tag stores, confirmation too strict, form/launcher variants), NOT captcha or IP throttling. ~24-39
of 75 confirmed delivered. Verdict is double-send-safe. The **residential proxy is wired** (ProxyBase,
residential+rotating, opt-in via a gitignored Server #1 `.env.proxy`); SI cost ~0.97 MB/store
images-blocked. NOTE: the proxy lifts LOADING/reach but CANNOT carry a send (ADR-0006: 0/9 via proxy vs
2/11 direct), so sends go direct.

**Next: prove conversion (0 bookings so far).** A real HITL send batch on the free channels (SI + clean
vendors + captcha-free contact forms) to get the first booking, then decide what is worth scaling.

