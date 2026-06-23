# Research: vendor universe (harvested 2026-06-22)

## Detection vs injection gap (the whole volume thesis)
`tools/chatdetect/scripts/signatures.py` DETECTS 62 vendors.
`tools/chatbot-breaker/send_no_ai.py` INJECTS into 1 (Gorgias, via `window.GorgiasChat`).
Every vendor we add to the injector multiplies reach.

## The 62 detected vendors, by category
- **live-chat (target):** intercom, drift, crisp, tawk.to, livechat, olark, tidio, chatra,
  smartsupp, jivochat, purechat, chatlio, liveagent, chaport, channel-io, liveperson,
  userlike, comm100, livehelpnow, zoho-salesiq
- **helpdesk (target):** zendesk, freshchat, freshworks-widget, gorgias, helpscout,
  reamaze, kustomer, gladly, front, helpcrunch, hubspot-chat, pylon, plain
- **ecommerce-chat (target):** shopify-inbox, shopify-ai-chat*, richpanel, delightchat,
  zipchat, gohighlevel
- **open-source-chat (target):** chatwoot, rocket-chat, tiledesk
- **ai-chat (SKIP - already have AI):** ada, chatbase, voiceflow, landbot, typebot,
  botpress, dialogflow, yellow-ai, haptik, forethought, wonderchat, chatling, sitegpt,
  docsbot, customgpt, hoory, kommunicate  (*shopify-ai-chat skip too)

## Qualification rule
Target = brand has a chat widget in the live-chat / helpdesk / ecommerce-chat /
open-source categories AND no AI. Live-chat widgets are human-only by default, so most
qualify. Skip anything in the ai-chat category.

## Priority candidates (build adapters in store-count order)
Best guesses pending exact counts: Shopify Inbox (default on huge slice of Shopify,
human-only), Tidio, Tawk.to, Crisp, Intercom, Zendesk, LiveChat. Gorgias already done.

## Per-vendor send feasibility (to confirm during build)
- Clean JS send API: Crisp (`$crisp` message:send), Drift (api), Gorgias (done).
- Prefill-then-confirm: Intercom (`showNewMessage`).
- DOM automation (find composer, type, click send): the rest. signatures.py already
  carries each vendor's selectors + runtime globals to hook.
