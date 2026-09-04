# Bug fixing, 2026-09-01

**Status (2026-09-01):** sending restarted after a 4-day outage. Root cause was supply
exhaustion, not a crash. All figures below are dated snapshots, not current facts.

Every number here is reproducible. Re-run the commands rather than trusting the values.

---

## Analysis 1: Attempted / Successful / Failed

Per-day send outcomes across all 7 send boxes (cx23, s3, s4, s5, s6, s7, s8).

Source: `/root/chat-outreach-engine/telemetry.jsonl` on each send box.
A row is counted when `phase == "outcome"`. It is Successful when
`action == "sent"` AND `detail` starts with `delivered` (this covers both
`delivered` and `delivered_ack:<id>`; filtering on `detail == "delivered"` alone
undercounts and has caused a wrong "vendor is dead" call before).

| day | attempted | successful | failed | rate |
|---|---|---|---|---|
| 2026-08-24 | 378 | 34 | 344 | 9.0% |
| 2026-08-25 | 7,057 | 1,752 | 5,305 | 24.8% |
| 2026-08-26 | 4,762 | 879 | 3,883 | 18.5% |
| 2026-08-27 | 2,925 | 399 | 2,526 | 13.6% |
| 2026-08-28 | 94 | 10 | 84 | 10.6% |
| 2026-08-29 | 179 | 38 | 141 | 21.2% |
| 2026-08-30 | 74 | 29 | 45 | 39.2% |
| 2026-08-31 | 6,179 | 344 | 5,835 | 5.6% |
| 2026-09-01 (partial) | 13,257 | 660 | 12,597 | 5.0% |
| **TOTAL** | **34,905** | **4,145** | **30,760** | **11.9%** |

Reproduce (per box, then sum):

    ssh <a send box> 'python3 - <<PY
    import json
    from collections import defaultdict
    a=defaultdict(int); d=defaultdict(int)
    for ln in open("/root/chat-outreach-engine/telemetry.jsonl",errors="replace"):
        try: o=json.loads(ln)
        except Exception: continue
        if o.get("phase")!="outcome": continue
        day=str(o.get("ts",""))[:10]
        a[day]+=1
        if o.get("action")=="sent" and str(o.get("detail","")).startswith("delivered"): d[day]+=1
    for k in sorted(a): print(k,a[k],d[k])
    PY'

---

## Analysis 2: deliv_start / deliv_end / GAINED

Per-day movement of the ledger's lifetime delivered counter, read off the pump's own
heartbeat. This is an independent second opinion on Analysis 1: Analysis 1 counts events
on the send boxes, Analysis 2 counts state in the ledger on b1. They should roughly agree.

Source: `/root/flows-orchestrator/pump.log` on b1, lines matching
`synced(delivered=N) ... total=Q`. pump.sh writes one every ~5 minutes.

| day | deliv_start | deliv_end | GAINED | queue_end |
|---|---|---|---|---|
| 2026-08-22 | 33,978 | 35,770 | 1,792 | 1,348 |
| 2026-08-23 | 35,770 | 35,770 | 0 | 1,348 |
| 2026-08-24 | 35,770 | 35,788 | 18 | 1,348 |
| 2026-08-25 | 35,788 | 37,637 | 1,849 | 1,351 |
| 2026-08-26 | 37,637 | 38,545 | 908 | 2,543 |
| 2026-08-27 | 38,569 | 38,971 | 402 | 1,448 |
| 2026-08-28 | 38,971 | 38,981 | 10 | 1,451 |
| 2026-08-29 | 38,981 | 39,020 | 39 | 1,451 |
| 2026-08-30 | 39,020 | 39,049 | 29 | 1,451 |
| 2026-08-31 | 39,049 | 39,429 | 380 | 70,345 |
| 2026-09-01 (partial) | 39,433 | 40,170 | 737 | 57,110 |

Reproduce:

    ssh <server-1> 'grep synced /root/flows-orchestrator/pump.log'

`queue_end` is the count of domains that are sendable but not yet sent. A flat
`queue_end` near zero across consecutive days is the signature of supply exhaustion,
and is what Aug 23 to Aug 30 shows (1,348 to 1,451, never moving).

---

## Bug fixed: what failed

### 1. Sending died 2026-08-27 midday and stayed dead four days

Not a crash. Every cron, watchdog and daemon was alive and correct the whole time.
The ledger reached **zero never-attempted domains**, and the last 1,448 wired-vendor
domains all carried `build_fails=2`, so the residue guard in `fm_supply.sh` had already
dropped them. With nothing buildable, `fm_supply` logged "no candidates" every 15 minutes,
`pump_cycle` queued nothing, and the senders had nothing to do.

### 2. The alarms worked. The response did not.

This is the important one. `delivery_alarm.py` fired **78 times** during the outage.
`dryout_alarm.py` tracked idle time correctly and reached `due=True` at
2026-08-28T03:56 after 16 hours at `queue=0, attempts/min=0.0`.

The monitoring was not blind. It was accurate and loud for days, and the machine
stayed dead regardless. Nothing connects an alarm to an action.

Check:

    ssh <server-1> 'grep -c "alerting=True" /root/flows-orchestrator/delivery_alarm.log'
    ssh <server-1> 'grep "due=True" /root/flows-orchestrator/dryout_alarm.log | head'

### 3. The 2026-08-28 intervention fixed the wrong layer, unverified

414,930 domains were loaded and detection was restored to 4,335/hr, then reported as
fixed. That supply was 86% Shopify Inbox, which has no working adapter, so **sending
never resumed**. Aug 28, 29 and 30 produced 10, 38 and 29 deliveries while the fleet
was being described as healthy.

"Detection is running" was treated as a proxy for "sending is running". Those two had
already decoupled. Three further days were lost before the send side was examined.

### 4. Land rate was decaying before the stop

24.8% (Aug 25) to 18.5% (Aug 26) to 13.6% (Aug 27), as the best remaining domains were
consumed.

### 5. The restart runs at a fifth of the old quality

5.0-5.6% versus Aug 25's 24.8%, because every domain in the current queue has already
rejected us once. Historical first-attempt land rate is 31.7%
(39,032 delivered / 123,261 attempted, wired vendors, all time).

### Cost

At Aug 25's rate the week should have produced roughly 12,000 deliveries. It produced
4,145. Most of the ~8,000 gap is the four-day outage, not the land-rate decline.
