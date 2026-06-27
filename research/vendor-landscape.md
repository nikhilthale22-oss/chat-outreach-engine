# Chat-vendor landscape (apparel pool, 2026-06-27)

Store counts from the StoreLeads apparel pool (2,212 stores, `installed_apps_names`). The build path
depends on the SEND mechanism, established by docs recon + live probes (probes are the source of truth;
docs misled on Tawk's iframe and on whether some have a send API).

Counts below are the apparel pool; the broader Shopify 5-10M pool shows the same leaders at larger
scale (Zendesk 654, Re:amaze 131, Intercom 98, HelpScout 49).

| vendor | stores | send mechanism | build path | status |
|---|---|---|---|---|
| Gorgias | 484 | API (`GorgiasChat.sendMessage`) | hand-written class | done (not delivery-confirmed) |
| **Zendesk** | **174** | **API** (`zE('messenger','sendMessage')`) / Classic is DOM-only | api-send or DOM (probe-dependent) | inconsistent load; see notes |
| Tidio | 59 | DOM-drive | WidgetDriver config | done + real-send proven |
| **Re:amaze** | **44** | DOM-drive (`Reamaze.popup()`); requires name+email (reply path!) | WidgetDriver config | deferred: popup opens a help-center lightbox, not a chat composer |
| Intercom | 32 | API (`Intercom('startConversation', msg)`; showNewMessage only prefills) | ApiVendorConfig over ApiSendDriver | BUILT, NOT send-verified |
| LiveChat | 15 | DOM-drive (no transmit method) | WidgetDriver config (frame by livechatinc.com) | built + verified to composer |
| Tawk | 14 | DOM-drive | WidgetDriver config (frame by about:srcdoc marker) | done + real-send proven |
| HelpScout | 11 | DOM-drive (Beacon; "Ask" is a fill+Send form) | WidgetDriver config (frame by #beacon-container) | built + verified to composer |
| Chatra | 10 | DOM-drive (no transmit method) | WidgetDriver config (frame by chatra.io) | built + verified to composer |
| Crisp | 8 | API (`$crisp message:send`) | hand-written class | not built (low count) |

## The strategic split

- **DOM-drive family (WidgetDriver configs):** Tidio, Tawk, Re:amaze, LiveChat, Chatra, HelpScout. The
  proven, cheap path - a config + (when the widget is in an iframe) a frame resolver. dom_echo confirms.
- **API-send family (hand-written, Gorgias-style):** Gorgias, Zendesk, Intercom, Crisp. These transmit
  via a JS call - no DOM typing. Zendesk (174) + Intercom (32) are the two biggest unbuilt vendors, so the
  api-send path is the single largest remaining reach, but it is a different mechanism (build a small
  ApiSendAdapter that does open -> newConversation/sendMessage -> confirm via the API callback).

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
- **Zendesk DEFERRED despite being the biggest (654).** Probing showed it is unreliable headless: ~half
  the stores never initialise `zE` (the snippet is inert, like a dead Tidio account), and of those that
  do, the DOM composer surfaced only intermittently (present on sunwarrior.com on one run, absent on the
  next). Its modern messaging send is also an async multi-step API (newConversation -> sendMessage), not
  a one-call send. Zendesk needs a dedicated session (decide DOM-drive on the stores that render a
  composer vs the messaging api-send flow) rather than a flaky overnight config.
