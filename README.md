**Status (2026-09-04):** engine library, 251 tests, 15 vendor adapters. The production
orchestrator that runs it lives on the servers, not here. See [docs/PRODUCTION.md](docs/PRODUCTION.md).
Sending was stopped on 2026-09-04 because the queue ran dry; delivery rate had fallen from
about 25 percent to about 5 percent over the previous week. That is the problem this repo
was made public to get help with.

# chat-outreach-engine

Reaches ecommerce brands by dropping a short pitch inside the live chat widget already
installed on their own website. Tidio, Tawk, Gorgias, Chatra and so on. Never cold email
(ADR-0001). One machine, the same steps on every store, with a small per-vendor adapter
that knows how to drive that vendor's widget.

## If you are new, read in this order

1. This file, then [CONTEXT.md](CONTEXT.md). CONTEXT is the glossary. The code and docs
   use its words strictly: Brand, Pitch, Adapter, Widget Driver, Ledger, Stage.
2. [docs/PRODUCTION.md](docs/PRODUCTION.md). What actually runs, on which box, and which
   files are not in this repo. Read this before forming a theory about production.
3. [docs/notes/2026-09-01-bug-analysis.md](docs/notes/2026-09-01-bug-analysis.md) and
   [docs/notes/2026-09-04-state.md](docs/notes/2026-09-04-state.md). The evidence of the
   current problem, with the queries that produced every number.
4. [docs/adr/](docs/adr/). Eight decisions and why. ADR-0007 and ADR-0008 explain the shape
   of the code.
5. [PENDING.md](PENDING.md) for open items, [CHANGELOG.md](CHANGELOG.md) for what changed
   and when, [docs/STATUS-LOG.md](docs/STATUS-LOG.md) for the dated history that used to
   live at the top of this file.

## How it works

```
domain
  |
  v  detect/     fetch the homepage, match it against 62 vendor signatures -> vendor or none
  |
  v  route/      vendor -> send method, or a first-class skip (no widget, gated, unsupported)
  |
  v  send/       open a real Chromium, load the store, open the widget, reach the composer,
  |              type the pitch, pass any email gate, confirm delivery was observed
  v
ledger.py       every domain, its Stage, vendor, variant and outcome; never pitch twice
```

`pipeline.py` is that unit for one store. `batch.py` runs it concurrently over a list.
`widget_driver.py` is the shared engine for every DOM-driven vendor; a vendor is a config
over it, not a class (ADR-0007). `api_send_driver.py` is the same idea for vendors that
expose a JavaScript send call. `reply_watcher.py` watches one inbox for replies, since every
vendor emails the address left at the gate (ADR-0002).

## Folder map

| path | what |
|---|---|
| `src/chat_outreach_engine/detect/` | vendor signatures and the detector |
| `src/chat_outreach_engine/route/` | registry of vendor to method, and the router |
| `src/chat_outreach_engine/adapters/` | one file per vendor: the config or class that drives its widget |
| `src/chat_outreach_engine/widget_driver.py` | the shared browser driver, 1,200 lines, most of the engine |
| `src/chat_outreach_engine/pipeline.py`, `batch.py` | the per-store unit and the concurrent runner |
| `src/chat_outreach_engine/ledger.py` | SQLite record of every brand and outcome |
| `src/chat_outreach_engine/reply_watcher*.py` | IMAP reply capture |
| `src/chat_outreach_engine/cli.py`, `batch_cli.py` | command line entry points |
| `send/`, `scale/`, `capture/`, `ops/` | phase folders from PLAN.md; `send/headed/` holds the adapter registry, the rest are placeholders |
| `tests/` | 251 unit tests (250 pass, 1 skipped), offline, using fixtures in `tests/fixtures/` |
| `research/` | the spike scripts and findings per vendor. Frozen history. Many read server paths and will not run locally |
| `docs/adr/` | decisions |
| `docs/notes/` | dated evidence of production state |
| `PLAN.md` | the blueprint the phase folders follow |
| `CLAUDE.md`, `.ralphy/` | rules for the AI coding tools Nikhil builds with. Safe to ignore |

## Running it locally

Requires Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                  # creates .venv from uv.lock
uv run playwright install chromium       # the browser the driver launches
uv run pytest -q                         # 251 tests, no network needed
```

Dry-run one store through the whole pipeline without sending:

```bash
uv run python -m chat_outreach_engine.cli --help
```

Live sends need a reply address in `REPLY_EMAIL` and a clean outbound IP. Datacenter IPs
get blocked by many storefronts, which is why production runs from dedicated boxes.
Do not send real pitches to real stores from a laptop while testing; use the dry-run path.

## Things that will trip you up

- The servers do not run this checkout. They run a June snapshot plus an orchestrator that
  is not here. A fix in this repo reaches production only when Nikhil copies it over.
- The research scripts import server-only paths at module load. `pytest` is scoped to
  `tests/` for that reason. Run a research script only by explicit path, on a server.
- Every throughput or delivery number written in any doc here drifted within days of being
  written. Treat them as dated snapshots. The queries in `docs/notes/` regenerate them.
- Delivery is only counted when observed: a token echoed in the rendered thread, a wire ack,
  or a cleared composer (ADR-0003). A terminal "200" is not a delivery.

## Stack

Python, uv, pytest, Playwright, SQLite. Heavy runs happen on Hetzner boxes, not a laptop.
