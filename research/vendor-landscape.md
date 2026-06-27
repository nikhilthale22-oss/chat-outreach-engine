# Chat-vendor landscape (apparel pool, 2026-06-27)

Store counts from the StoreLeads apparel pool (2,212 stores, `installed_apps_names`). The build path
depends on the SEND mechanism, established by docs recon + live probes (probes are the source of truth;
docs misled on Tawk's iframe and on whether some have a send API).

| vendor | stores | send mechanism | build path | status |
|---|---|---|---|---|
| Gorgias | 484 | API (`GorgiasChat.sendMessage`) | hand-written class | done (not delivery-confirmed) |
| **Zendesk** | **174** | **API** (`zE('messenger','sendMessage')` / `newConversation`) | api-send (Gorgias-style); Classic widget is DOM-only | NOT built - decision needed |
| Tidio | 59 | DOM-drive | WidgetDriver config | done + real-send proven |
| **Re:amaze** | **44** | **DOM-drive** (`Reamaze.popup()`); requires name+email (reply path!) | WidgetDriver config | needs a re-probe (SDK global init) |
| Intercom | 32 | API (`Intercom('startConversation', msg)`; showNewMessage only prefills) | api-send (Gorgias-style) | NOT built - decision needed |
| LiveChat | 15 | DOM-drive (no transmit method) | WidgetDriver config (frame by livechatinc.com) | built + verified to composer |
| Tawk | 14 | DOM-drive | WidgetDriver config (frame by about:srcdoc marker) | done + real-send proven |
| HelpScout | 11 | DOM-drive (Beacon, prefill only) | WidgetDriver config | needs a re-probe (open) |
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
  reply-capture thesis - we get to leave our email. Worth prioritising once its open is nailed.
