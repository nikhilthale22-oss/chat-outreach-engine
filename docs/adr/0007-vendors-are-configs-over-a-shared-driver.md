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

## Validated by Tawk (2026-06-27)

Tawk.to became the second vendor and confirmed the seam pays off: it is a `VendorConfig`, not a class
(no new flow code for the visitor send). It did require the driver to grow ONE capability the config
declares - same-origin iframe widgets resolved by a content marker (`widget_frame_marker`), because
Tawk's v4 panel lives in an `about:srcdoc` iframe with no stable URL. That is the intended pattern: the
shared driver gains a capability when a vendor needs it (added test-first, behind config defaults so
existing vendors are untouched), and the next iframe vendor reuses it for free. Also added as config
knobs the same way: a `callback_flag` confirm (onChatMessageVisitor) and a `by_text` entry strategy.
Tidio's path stayed byte-identical (the new fields default to its shape). See research/tawk-injection.md.

## Validated again by Zendesk (2026-06-28)

Zendesk - the biggest unbuilt vendor - had been DEFERRED as probably api-send (its modern messaging
"send" is an async `newConversation -> sendMessage`) and "too flaky headless". Live probing overturned
both: the modern messaging widget renders a real composer in a srcdoc/blank iframe (titled "Messaging
window", no URL), so it is DOM-drive exactly like Tawk, and the "flakiness" was a slow-bundle race plus
a probe bug, not real. It became a `VendorConfig` (`ZENDESK`) that needed **zero new driver code** - it
reuses Tawk's `widget_frame_marker` (frame-by-content) and `dom_echo` confirm, with `open_js` firing
every `zE` open verb (each guarded) so one config covers both widget families. This is the payoff the
seam was for: the second iframe vendor (Tawk) cost one driver capability; the third (Zendesk) cost
nothing. Verified 5/5 to composer via the shipped path. The one driver addition this round - a `dry_run`
flag on `send()` that reaches the composer and returns without transmitting - is the unattended-safe
verify-to-composer proof and applies to every vendor, not just Zendesk. See research/zendesk-injection.md.
