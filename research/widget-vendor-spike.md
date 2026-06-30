# Untapped-vendor spike (2026-06-30)

Goal: grow the pool by activating the StoreLeads-tagged-but-undriven vendors. For each candidate,
discover the SDK global + open verb + composer + frame situation on LIVE stores, write a VendorConfig
(ADR-0007), and measure verify-to-composer on a random sample via the production path
(`WidgetDriver.send(dry_run=True)` - reaches the composer, transmits nothing).

Source lists: extracted column-aware from `domains_export.csv` (321k rows, has `technologies` /
`installed_apps_names` / `tags`), excluding stores that already run an AI bot (ChatBot/Gobot/ManyChat/
Drift/Intercom/Lyro/...). These per-vendor lists are a subset of the full StoreLeads pool, big enough
to spike + verify. Harnesses: `research/widget_discover_v2.py`, `research/widget_reprobe.py`,
`research/verify_vendor.py`.

## Verdicts

| vendor | SDK global | open verb | composer | verify-to-composer | verdict |
|---|---|---|---|---|---|
| **Olark** | `window.olark` | `olark('api.box.expand')` | page DOM `textarea[id^='olark-custom-element']` | **14/20 (70%)** | **SHIPPED** |
| **Zoho SalesIQ** | `window.$zoho.salesiq` | `$zoho.salesiq.floatwindow.visible('show')` + `chat.start()` | any `textarea` in an `about:blank` frame | **9/20 (45%)** after selector fix (was 35%) | **SHIPPED** |
| Kustomer | `window.Kustomer` (live) | `Kustomer.open()` | none surfaced (launcher-click 1/6 = a misclick to an AI bot) | ~0 | DROP - no headless-drivable composer |
| Richpanel | `window.Richpanel` (live) | `Richpanel('open')` and variants | none surfaced even with launcher-click (0/6) | 0 | DROP - no headless-drivable composer |
| Re:amaze | `window.Reamaze` | `Reamaze.popup()` | composer behind a menu entry in an about:blank frame | 0/8 (popup opens no detectable menu frame headless; ~3/8 stale) | DROP - menu does not render headless |
| Freshchat | `window.fcWidget` | `fcWidget.open()` | n/a | global absent across sample | DROP - tags stale |
| Gladly | `window.Gladly` | `gladlyChat.show()` | none | global mostly absent | DROP - stale + enterprise |
| Freshdesk | `window.FreshworksWidget` | `FreshworksWidget('open')` | n/a (ticket form, not chat) | not pursued | DROP |

**Widening round 2 (launcher-click spike, 2026-06-30).** Built a generic launcher-click discovery
(`research/launcher_discover.py`): if a JS `open()` surfaces no composer, find + click the floating
launcher (bottom-right / chat-ish, in page or any frame), re-scan all frames. Result: it did NOT
unlock Kustomer (1/6, and that 1 was a cookie-banner misclick that landed on an unrelated "Ask AI
anything" bot) or Richpanel (0/6 - globals live on ~all stores, but no composer mounts headless even
after a click). Re:amaze (`research/reamaze_probe.py`): `popup()` opens no detectable menu frame
headless (the probe caught only unrelated frames - a Loox reviews carousel, a privacy notice), ~3/8
stale. **Verdict: among the StoreLeads-tagged untapped vendors, only Olark and Zoho are headless-
drivable; Richpanel/Kustomer/Re:amaze do not surface a composer in a headless browser and are dropped.**
The **Zoho lift** came from the spike though: the generic textarea scan reached 8/12, exposing that the
config's `textarea#msgarea, textarea[placeholder*='message']` selector missed the id-less / varied-
placeholder skins (and, being the frame marker too, failed to resolve the about:blank frame). Broadened
to any `textarea` -> 35% to 45% on the same sample.

## Detail

- **Olark (clean win, like Crisp).** Composer is page-level; Olark's storage.html iframe holds state
  only. The name/email inputs share the `olark-custom-element-` id prefix but are `<input>`, so scoping
  the composer to `<textarea>` keeps it on the message box. 70% reach; the 30% miss is 4/20 stale
  `no_olark_api` + 2/20 `no_composer` (a skin that hard-gates behind a pre-chat form).
- **Zoho SalesIQ (works, modest).** Composer `#msgarea` lives in an `about:blank` iframe with no
  stable URL, so the config resolves it by in-frame content marker (the same mechanism as Tawk's
  about:srcdoc). 35% reach; 9/20 `no_composer` = Zoho gating the box behind a pre-chat/entry step the
  current open verbs do not fully surface. A future spike (entry-click before composer) would lift it;
  35% is shippable now.
- **Kustomer / Richpanel - real installs, but no JS-openable composer.** Globals are live on nearly
  every store, but firing the documented open verbs headless never mounts the chat iframe (the frame
  tree stays Shopify web-pixels / paypal / youtube only). These widgets appear to mount the composer
  on a real launcher click, not a JS API call - their own spike, deferred. (One Kustomer-tagged store
  had migrated to `client.chatwill.ai` - tag rot.)
- **Freshchat / Gladly / Freshdesk - tags stale in this sample.** Globals absent on nearly all; the
  tagged installs have mostly been removed. Not worth a config until a fresher tagged list shows they
  are live. Freshdesk's on-site widget is a ticket form, not a chat composer, regardless.

## Net pool impact

Two new drivable vendors. At the full StoreLeads pool: Olark ~218 x 70% ~= 150 deliverable, Zoho
~268 x 35% ~= 94 deliverable. Modest next to Gorgias (+6,220, awaits one HITL verification send) and
a richer StoreLeads export, but a clean return on the spike and they round out the untapped-vendor item.
