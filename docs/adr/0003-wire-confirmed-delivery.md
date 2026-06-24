# 0003 - An Adapter reports a Pitch sent only when delivery is observed

Status: accepted (2026-06-24)

A vendor Adapter returns sent=True only when it has positively observed the Pitch leave the
browser to the vendor's backend, not merely when the send code ran without throwing. For
Tidio this means capturing the `visitorNewMessage` websocket frame carrying the Pitch text
before reporting success; an unconfirmed attempt returns sent=False with a retryable detail.
The Ledger advances a Brand to Pitched only on that confirmed signal.

Why it is recorded here: it is hard to reverse (the whole engine's trust model and the
Ledger's accounting depend on sent meaning delivered, and the Reply Watcher / funnel report
build on it), surprising without context (the obvious shortcut is "the API call returned, so
it sent" - which produced a real false positive the first time, a Brand marked Pitched with
nothing delivered), and a real trade-off (wire confirmation costs extra waiting and per-vendor
reverse-engineering, but without it the engine silently burns prospects and lies in its own
numbers). The GorgiasAdapter does NOT yet meet this bar (it returns sent=True unconditionally),
so it is disabled in the batch runner until it does. This ADR stops anyone from "simplifying"
an Adapter back to fire-and-assume-success.
