# Changelog

## 2026-06-27

- **Slice 1: v4/Lyro composer fix.** Fresh Tidio accounts now ship the v4 "Lyro" widget that opens to a Home screen ("Chat with Lyro" / "Chat" entry), not a direct composer; the old `ENTRY_LABELS` missed it and `send()` returned `no_composer`. Added `TidioAdapter._pick_entry_label(button_texts)` pure resolver (v3 labels first, then "Chat with Lyro", then exact "Chat" nav) and rewired `_click_entry`. Live-confirmed delivered through the real adapter. (`adapters/tidio.py`, `tests/test_tidio_adapter.py`)
- **`_target_url` seam.** The adapter accepts an explicit-scheme URL (http test pages, http-only stores), bare domains still get https. (`adapters/tidio.py`)
- **Gate liveness.** Assessment now GETs the Tidio loader: 200 -> pass; 401/403/404/410 (suspended/expired/removed account) -> Dead `tidio loader dead`; timeout/5xx/conn-error -> `loader unknown`, which stays Queued/retryable so a transient blip never false-kills a live store. Drops dead-account stores over HTTP, ~3.5x fewer wasted browser launches. Extends ADR-0005. (`batch.py`, `tests/test_gate_liveness.py`, `docs/adr/0005`)
- **Reply Watcher auto-reply filter.** CSAT / out-of-office / automated replies no longer false-positive as `Replied`. Filtered on body/subject text, NOT on a no-reply sender (Tidio's legit reply notification itself comes from a no-reply address). (`reply_watcher.py`, `tests/test_reply_watcher.py`)
- **Foundation measured (not assumed).** Random N=40 through the production path: gate-pass ~42%, but ~70% of gate-passed are dead Tidio accounts, so ~7.6% net deliverable (~200 live stores), not the old ~450. Diagnosis proved `no_tidio_api` is dead accounts (loader 403/404), not our automation.
- 61 tests green.
