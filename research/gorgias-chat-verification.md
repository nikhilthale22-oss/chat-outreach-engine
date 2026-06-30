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

The drivable chat widget exposes `window.GorgiasChat`. Random-sample scans of the qualified
Gorgias-tagged pool (`research/gorgias_chatlive.py`, waits for `window.GorgiasChat`):

- **CHAT-LIVE (window.GorgiasChat present): 0 / 140** (a 50-store scan + a 90-store scan; a third 90
  was running and only extends the denominator).
- bridge-only (only `window.GorgiasBridge` - the Gorgias bundle-loader for email / contact-forms,
  live chat OFF): ~87 / 140 (62%).
- no-gorgias (stale tag or bot-blocked): ~49 / 140 (35%). error: 4 / 140.

0/140 puts the 95% upper bound on the chat-live rate at ~2.6%, i.e. AT MOST a couple hundred across
the full 6,220 and realistically near zero.

Diagnostic (`research/gorgias_diag.py`) confirmed the mechanism: tagged stores load
`config.gorgias.chat/bundle-loader/...` + `config.gorgias.help/.../replace-mailto-script.js` and expose
`window.GorgiasBridge`, but NOT `window.GorgiasChat`. They use Gorgias for HELPDESK / email / contact
forms; the on-site chat widget is configured off. The StoreLeads "Gorgias" tag flags the Gorgias
platform, which over-counts the chat-widget subset massively.

**Implication:** the +6,220 was not 6,220 chat stores. The drivable Gorgias-CHAT pool is the chat-live
subset, ~0% of 140 random stores. Gorgias is NOT the "biggest cheap win" the capacity map assumed -
strike it. There was no chat-live store in-sample to fire a send-path proof at; firing at a bridge-only
store correctly returns `no_gorgias_chat`.

## What this means for the engine

- Keep the hardened adapter: it is the correct shape and will confirm honestly IF a chat-live Gorgias
  store is ever pitched. Always re-qualify a Gorgias list with `gorgias_chatlive.py` first - never pitch
  off the raw tag.
- Strike the +6,220 from the capacity math. The real near-term pool growth is the clean composer
  vendors (Olark, Zoho, plus the proven Tidio/Tawk/Zendesk/Chatra/LiveChat/Crisp) and Shopify Inbox.
- A real send to prove the path is HITL and needs a genuinely chat-live store; with 0/50 there was none
  in-sample to fire at.
