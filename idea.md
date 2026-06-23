# Chat-Outreach Engine - Idea

## What it is
A system that pitches ecommerce brands INSIDE their own live chat widget. It finds a
brand's chat widget, confirms the brand has no AI behind it, opens the widget, and sends
a short pitch offering to build them an AI chatbot. Replies come back to a monitored
inbox and get tracked through to a booked call.

## Who it's for
Us (Postlist / Mercwise outbound). The recipients are ecommerce / Shopify brands running
a human-only chat widget.

## The channel conviction (locked)
The channel is chat-widget injection. We do NOT use cold email, ever (see
docs/adr/0001). Volume grows by supporting MORE chat vendors, not by switching channels.

## Scope (locked 2026-06-22)
The full chat-widget outreach engine as one product:

    source brands -> detect chat vendor -> qualify (no AI) -> inject pitch (per-vendor)
    -> capture replies -> ledger

The multi-vendor injector is the first slice. Out of scope for now: the large-scale
domain scanner (production `chatbot-outreach` on Server #1). We consume its output, we do
not rebuild it here.

## The volume thesis
`chatdetect` already DETECTS 62 chat vendors. The injector only SENDS into 1 (Gorgias).
Each new vendor adapter multiplies the reachable universe. Live-chat vendors are mostly
human-only by default, so they qualify for the "you don't have an AI chatbot" pitch
easily.

## What "obviously good" looks like
- One repo, one spine, tests, no dead hardcoded paths.
- Injector works across the top 5-6 vendors by store count.
- Every send and every reply is logged; we can see reply rate per vendor and per pitch
  variant.
- We never run dry on a vendor without already knowing the next one to add.
