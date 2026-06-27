# 0007 - A DOM-drive vendor is a VendorConfig over a shared WidgetDriver, not a hand-written class

Status: accepted (2026-06-27)

Most Chat Widgets are driven the same way: launch a stealthed browser, load the site, wait for
the widget to come up, open it, reach the composer (sometimes past a Home screen), type the Pitch,
get past the email gate, and confirm delivery. What differs between vendors is *data*, not control
flow: the scope selector the widget lives under, the JS predicate that says it is ready, the labels
that open a conversation, how the email gate works, and how a send is confirmed.

We therefore split this "DOM-drive family" into two pieces: a shared `WidgetDriver` that owns the
flow, and a `VendorConfig` that supplies one vendor's data. Tidio is the reference vendor and is now
a `VendorConfig` (`TIDIO`) over `WidgetDriver`; `TidioAdapter` is a thin delegator that keeps the
`Adapter` public surface (`vendor` + `send()`) unchanged. **Adding a DOM-drive vendor (Crisp, Tawk,
Shopify Inbox, ...) is a new `VendorConfig`, not a new class.** This is the breadth lever: the chat
channel scales by covering more vendors cheaply, and a config is reskin-proof in a way that copied
flow is not.

## The boundary: API-send vendors stay hand-written

A vendor whose SEND is a JS API call rather than a DOM drive does NOT belong on the shared driver.
Gorgias is the case in point: it transmits via `window.GorgiasChat.sendMessage()` and never touches
the composer, the shadow DOM, the entry labels, or the wire-frame confirmation. Folding it into the
config would add mutually-exclusive `if api: ... else: ...` branches to every step - an abstraction
that is really two wearing one coat. Gorgias stays its own ~50-line `Adapter`. The rule: **same
control flow + different data -> a config; different control flow -> its own class.**

## Reconciling the glossary

CONTEXT.md's `Adapter` term said "one Adapter per vendor". That is still true at the seam the
Injector sees (it dispatches on `vendor` to an object with a `send()` method), but an Adapter is now
realised two ways: a `VendorConfig` over the shared `WidgetDriver` for the DOM-drive family, or a
hand-written class for an API-send vendor that does not fit the shared flow.

## Why it is recorded here

Hard to reverse (every future DOM-drive vendor is built as a config against this seam; changing the
seam later means reworking all of them), surprising without context (the obvious move is to copy the
Tidio class per vendor, which is what we are deliberately not doing), and a real trade-off (a shared
driver constrains each vendor to the common flow and pays an indirection cost, in exchange for cheap,
uniform, reskin-proof vendor coverage; a vendor that needs genuinely different control flow is the
explicit escape hatch). Parity was held at the cut-over: every config-generated selector and JS
snippet was diffed against the old Tidio literals, the pure-logic tests moved with the code and stay
green, and the live send flow is the same code moved verbatim, re-proven by a real Tidio send.
