# What runs in production, and what is not in this repo

Written 2026-09-04 for someone reading this repo cold. Every number here is a dated
snapshot. The live truth is the ops dashboard and the ledger on Server 1, never a doc.

## The one thing to know first

**This repo is the engine library. The machine that runs it is not in this repo.**

The engine (`src/chat_outreach_engine/`) is what opens a store's page, finds its chat
widget, types a pitch and confirms delivery. Around it, on the servers, sits an
orchestrator that was written directly on Server 1 and never committed here. So if you
read this code and it does not match what the servers do, that is why. Ask Nikhil for a
read-only copy of the server folders before debugging production behaviour.

## The fleet (as of 2026-09-04)

Eight Hetzner boxes. Names are the labels used in logs and telemetry.

| box | role | what runs there |
|---|---|---|
| b1 (Server 1) | brain, sends nothing | ledger (SQLite, a few hundred thousand domains), `pump.sh` loop that builds queues and keeps senders alive, supply loader, detection, page builder, alarms, ops dashboard, Caddy serving flows.mercwise.com |
| cx23, s3, s4, s5, s6, s7, s8 | senders | a June rsync snapshot of this engine at `/root/chat-outreach-engine/`, a sender daemon that drains its own `queue_<box>.csv`, and writes `telemetry.jsonl` |

Work is sharded seven ways by a hash of the domain, so no two boxes ever touch the same
store. b1 copies each queue out and pulls each box's sent, attempts and telemetry files back.

## Files that exist only on the servers

On b1 under `/root/flows-orchestrator/`:

- `pump.sh`, `pump_cycle.py`, `pump_watch.sh`: queue build, shard, push, keep-alive
- `fm_supply.sh`: builds the per-store landing page the pitch links to. A store is only
  queued once its page exists. This gate, not hardware, has been the feed bottleneck before.
- `detect_selfhost.py`, `merge_s1.py`, `redetect_watch.sh`: paced detection and ledger merge
- `delivery_alarm.py`, `dryout_alarm.py`, `stage_alarm.py`, `ops_collect.py`: alarms and the
  nine-stage monitor (Supply, Detect, Merge, Build, Queue, Push, Attempts, Outcomes, HardAck)
- `ledger.db`: the domains table with vendor, detect status, delivery, country, stage

On each send box under `/root/chat-outreach-engine/`:

- the engine snapshot, `camp2k_send.py` (the per-message sender), the daemon script,
  `telemetry.jsonl`, `<box>_sent.jsonl`, `<box>_attempts.jsonl`

## The path a domain takes

```
StoreLeads export (Shopify + Woo, ~8M rows)
      |
      v  supply loader (b1)             filters by country allowlist, parks dead domains
ledger.domains
      |
      v  detection (b1, paced ~0.4 rps) static homepage fingerprint -> vendor or no_widget
      |                                  same code as src/chat_outreach_engine/detect/
      v  page builder (b1, fm_supply)    a store is queueable only once its page exists
      |
      v  pump_cycle (b1)                 shard 7 ways, order by vendor land rate, write queue_<box>.csv
      |
      v  sender daemon (each box)        one real Chromium per message via widget_driver.py
      |                                  outcome row -> telemetry.jsonl
      v  b1 folds outcomes back          delivered domains leave the queue for good
```

## Vendors and how they behave

The engine supports 15 adapters. In production only these are queued, because the others
either never deliver or deliver too rarely to be worth a browser launch:

tawk.to, tidio, gorgias, chatra, crisp, zendesk, zoho-salesiq, helpscout, zipchat, olark,
livechat, reamaze. Land rates per vendor as of 2026-09-04 are in
`docs/notes/2026-09-04-state.md`. They move week to week. Read the ledger, not the note.

Dead ends that were measured, not guessed, and should not be re-tried without new evidence:

- Shopify Inbox and the Shopify agent widget: sign-in gated, 0 verified deliveries across
  tens of thousands of stores. Skipped on purpose.
- Contact forms: interactive hCaptcha, 0 of 8 in both headed and proxied modes.
- A browserless HTTP send path: proven dead, see ADR-0008.

## Environment variables the engine reads

Names only. Values live in `.env` files that are gitignored and never left Nikhil's machines.

- Sending: `REPLY_EMAIL`, `CAMP_SEND_TIMEOUT`, `CAMP_NAV_TIMEOUT_MS`, `CAMP_READY_MAX_MS`,
  `CAMP_INIT_ROUNDS`, `CAMP_BLOCK_ASSETS`, `PW_EXECUTABLE_PATH`
- Debug: `CW_DIAG`, `CW_DIAG_NOSEND`, `CW_DUMP`, `CW_DUMP2`
- Reply watcher: `IMAP_USER`, `IMAP_APP_PASSWORD`
- Proxy fallback: see `proxy.py`, off by default (ADR-0006)

## Where the evidence lives

- `docs/notes/2026-09-01-bug-analysis.md`: per-day attempted, delivered, failed across the
  seven send boxes for the last week of August, with the exact queries used.
- `docs/notes/2026-09-04-state.md`: state of the ledger, country filter, vendor land rates,
  and the open items, as of the day this repo went public.
- `research/`: the spike findings per vendor, frozen. How each widget was reverse engineered.
- `docs/adr/`: the eight decisions that shaped the design, with reasons.
