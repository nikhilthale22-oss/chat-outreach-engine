# Crisp + Re:amaze injection (live probes, 2026-06-29)

Both were written off earlier and recovered in the one-way-pitch pivot (we only need to DELIVER the
pitch, which carries our website + cal link; no inbound reply path needed). Live discovery probes on
real stores (StoreLeads "Crisp" / "Re:amaze" tech tags) established the mechanics below. Both are
DOM-drive `VendorConfig`s over the shared `WidgetDriver` (ADR-0007), not new classes.

## Crisp  (adapters/crisp.py)

- **SDK:** `window.$crisp` (array-push API). Ready predicate `window.$crisp`.
- **Open:** `$crisp.push(['do','chat:open'])`. Some skins want `chat:show` first, so the config fires
  both, each guarded. Open lands directly on the composer (no Home screen / entry click).
- **Composer:** rendered IN THE HOST PAGE DOM (Crisp injects its chatbox into the page, NOT an
  iframe), a `<textarea placeholder="Compose your message...">`. Class names are hashed (`cc-*`), so
  the placeholder is the durable marker. No frame resolution needed (`widget_scope=None`).
- **Email gate:** none needed (one-way model). Confirm: `dom_echo`.
- **Probe result:** of 6 tagged stores, 4 had a live `$crisp` SDK and reached the composer on the
  page via `chat:open`; 2 had no SDK (stale tag). The static "Crisp" tag over-counts.

## Re:amaze  (adapters/reamaze.py)

- **SDK:** the embed sets `window._support` (config); the SDK loads LAZILY as `window.Reamaze`. Ready
  predicate `window.Reamaze` with a long timeout (30s) because it can be slow to appear.
- **Open:** `Reamaze.popup()` (the earlier `Shoutbox()` / popup-verb confusion was the blocker).
- **Composer:** the conversation renders in a same-origin `about:blank` iframe with NO stable URL
  (Tawk-style), a `<textarea placeholder="Enter your question or message here">`. Resolve the frame by
  content (`widget_frame_marker` = the composer placeholder), then drive the composer inside it.
- **Email gate:** none (one-way model). Confirm: `dom_echo`.
- **Probe result:** messier than Crisp. Of 7 tagged stores, 1 surfaced the composer cleanly via
  `popup()`; several had `_support` set but `window.Reamaze` had not loaded within the probe window
  (lazy SDK), and a couple had `Reamaze` but `popup()` did not surface a composer in time. So the
  long ready-wait matters, and measured reach is well below the raw tag count. Re-measure verify-to-
  composer at scale before trusting the rate.

## One-way model note

Neither vendor needs the email gate: the pitch itself carries mercwise.com + the cal link, so an
interested merchant contacts us. Both are `email_strategy="none"`, `confirm_strategy="dom_echo"`.
