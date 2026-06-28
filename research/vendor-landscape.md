# Chat-vendor landscape (apparel pool, 2026-06-27)

Store counts from the StoreLeads apparel pool (2,212 stores, `installed_apps_names`). The build path
depends on the SEND mechanism, established by docs recon + live probes (probes are the source of truth;
docs misled on Tawk's iframe and on whether some have a send API).

Counts below are the apparel pool; the broader Shopify 5-10M pool shows the same leaders at larger
scale (Zendesk 654, Re:amaze 131, Intercom 98, HelpScout 49).

| vendor | stores | send mechanism | build path | status |
|---|---|---|---|---|
| Gorgias | 484 | API (`GorgiasChat.sendMessage`) | hand-written class | done (not delivery-confirmed) |
| **Zendesk** | **174** | **DOM-drive** (messaging composer; the async sendMessage API is not needed) | WidgetDriver config (frame by "Messaging window" marker) | **built + verified to composer 5/5** (research/zendesk-injection.md) |
| Tidio | 59 | DOM-drive | WidgetDriver config | done + real-send proven |
| **Re:amaze** | **44** | DOM-drive (`Reamaze.popup()`); requires name+email (reply path!) | WidgetDriver config | deferred: popup opens a help-center lightbox, not a chat composer |
| Intercom | 32 | API (`Intercom('startConversation', msg)`; showNewMessage only prefills) | ApiVendorConfig over ApiSendDriver | BUILT, NOT send-verified |
| LiveChat | 15 | DOM-drive (no transmit method) | WidgetDriver config (frame by livechatinc.com) | built + verified to composer |
| Tawk | 14 | DOM-drive | WidgetDriver config (frame by about:srcdoc marker) | done + real-send proven |
| HelpScout | 11 | DOM-drive (Beacon; "Ask" is a fill+Send form) | WidgetDriver config (frame by #beacon-container) | built + verified to composer |
| Chatra | 10 | DOM-drive (no transmit method) | WidgetDriver config (frame by chatra.io) | built + verified to composer |
| Crisp | 8 | API (`$crisp message:send`) | hand-written class | not built (low count) |

## The strategic split

- **DOM-drive family (WidgetDriver configs):** Tidio, Tawk, **Zendesk**, Re:amaze, LiveChat, Chatra,
  HelpScout. The proven, cheap path - a config + (when the widget is in an iframe) a frame resolver.
  dom_echo confirms. Zendesk (the biggest) moved here after probing: its messaging widget renders a real
  composer, so no api-send is needed (research/zendesk-injection.md).
- **API-send family (hand-written / ApiSendDriver):** Gorgias, Intercom, Crisp. These transmit via a JS
  call - no DOM typing. Intercom (32) is now the main api-send vendor (built, not send-verified).

## Notes from the live probes

- iframe widgets mostly have a STABLE iframe URL (livechatinc.com, chatra.io, intercom.io, zendesk) ->
  resolve the frame by URL substring (`widget_frame_url`). Tawk is the exception (about:srcdoc) -> resolve
  by an in-frame content marker (`widget_frame_marker`).
- LiveChat and Chatra were both probed OFFLINE (team away): the composer is still reachable, but the
  online send path (live composer + Enter) vs offline (leave-a-message form / queued message) differs.
  Both are verified to the composer with the shipped code; a real online send is the remaining proof
  (like Tawk's allurepack send).
- Re:amaze requires name+email by default (contactMode "default"), so it is the best vendor for the
  reply-capture thesis - we get to leave our email. DEFERRED: `Reamaze.popup()` opened a help-center
  contact lightbox, not the live-chat shoutbox composer, and the SDK global loaded inconsistently. Needs
  a focused look at enabling/targeting the shoutbox widget.
- **Zendesk BUILT (2026-06-28) - the deferral was wrong.** A focused session overturned it: the
  "intermittent composer" was a slow-bundle race + a frame-filter bug, not real flakiness. The modern
  messaging widget renders a real composer in a srcdoc/blank iframe titled "Messaging window"; resolved
  by content marker + generous poll, it surfaces 5/5. DOM-drive, not api-send. The "~half never init zE"
  is the dead-account-lingering-tag problem (loader-liveness GET of `static.zdassets.com/ekr/snippet.js`
  filters it, like Tidio/Tawk). Raw counts over-count ~5x: only ~20-23% of grep-matched stores run live
  Zendesk. Real online HITL send still owed. Full trail: research/zendesk-injection.md.
