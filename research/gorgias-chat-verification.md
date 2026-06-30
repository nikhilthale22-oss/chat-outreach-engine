# Gorgias verification (2026-06-30)

Goal: verify the wired-but-unconfirmed Gorgias send path, and confirm the +6,220 "Gorgias pool" is
real drivable chat. Result: **the pool is largely illusory, and the adapter was returning a false
positive.** Two separate findings.

## Finding 1: the adapter never confirmed delivery (FIXED)

The old `GorgiasAdapter` was a hand-written class that called `window.GorgiasChat.sendMessage(pitch)`
and immediately returned `SendResult(True, "pitch_sent")` - no check that the message actually posted.
So even a "successful" Gorgias send proved nothing. Migrated Gorgias onto the existing **ApiSendDriver**
(an `ApiVendorConfig`, same family as Intercom), which confirms by `dom_echo_any`: the Pitch token must
render in the Messenger before it returns `delivered`; otherwise `no_delivery_confirmation`. This is the
honest send path the verification needed. (6 tests; suite 176 green.)

## Finding 2: the "Gorgias" tag is a HELPDESK tag, not a chat-widget tag

The drivable chat widget exposes `window.GorgiasChat`. A random-sample scan of the qualified
Gorgias-tagged pool (`research/gorgias_chatlive.py`, waits up to 20s for `window.GorgiasChat`):

- **CHAT-LIVE (window.GorgiasChat present): 0 / 50.**
- bridge-only (only `window.GorgiasBridge` - the Gorgias bundle-loader for email / contact-forms,
  live chat OFF): 33 / 50.
- no-gorgias (stale tag or bot-blocked): 16 / 50. error: 1 / 50.

Diagnostic (`research/gorgias_diag.py`) confirmed the mechanism: tagged stores load
`config.gorgias.chat/bundle-loader/...` + `config.gorgias.help/.../replace-mailto-script.js` and expose
`window.GorgiasBridge`, but NOT `window.GorgiasChat`. They use Gorgias for HELPDESK / email / contact
forms; the on-site chat widget is configured off. The StoreLeads "Gorgias" tag flags the Gorgias
platform, which over-counts the chat-widget subset massively.

**Implication:** the +6,220 was not 6,220 chat stores. The drivable Gorgias-CHAT pool is the chat-live
subset, ~0% of a 50-store random sample (so at best a low-single-digit % of the tag, a few hundred
across the full pool, found only by scanning thousands). Gorgias is NOT the "biggest cheap win" the
capacity map assumed. A larger parallel scan (180) is running to tighten the rate and surface the
chat-live minority, if any, for a single send-path proof.

## What this means for the engine

- Keep the hardened adapter: it is the correct shape and will confirm honestly IF a chat-live Gorgias
  store is ever pitched. Always re-qualify a Gorgias list with `gorgias_chatlive.py` first - never pitch
  off the raw tag.
- Strike the +6,220 from the capacity math. The real near-term pool growth is the clean composer
  vendors (Olark, Zoho, plus the proven Tidio/Tawk/Zendesk/Chatra/LiveChat/Crisp) and Shopify Inbox.
- A real send to prove the path is HITL and needs a genuinely chat-live store; with 0/50 there was none
  in-sample to fire at.
