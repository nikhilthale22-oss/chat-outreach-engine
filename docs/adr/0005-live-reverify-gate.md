# 0005 - Re-verify the widget against the live site before spending a browser launch

Status: accepted (2026-06-24)

Before the Batch Runner sends a Pitch, it re-checks the Brand's live HTML to confirm the
Chat Widget will actually load under automation - it does not trust a static vendor list or
a one-time scan. For Tidio this means requiring a direct `code.tidio.co/<id>.js` loader tag
(a store that injects Tidio via a Shopify app-embed only references tidioChatApi and never
initialises headless). A Brand that fails the gate is marked Dead, not sent.

Why it is recorded here: it is hard to reverse (the Assessment step and the Dead-vs-send
decision are built on it), surprising without context (the obvious assumption is "the scan
said vendor=tidio, so pitch it" - which wastes a full browser launch on dynamic-embed and
stale-tag stores that can never deliver, and inflates the apparent pool), and a real
trade-off (the gate adds a fetch and deads some Brands that a richer check might recover, in
exchange for not burning launches on un-loadable stores). Known limitation, accepted: the tag
being present still over-qualifies - many tagged stores do not initialise Tidio headless and
fail later as no_tidio_api - so the gate narrows but does not guarantee delivery. This ADR
stops anyone from pitching straight off the static scan without the live re-verify.
