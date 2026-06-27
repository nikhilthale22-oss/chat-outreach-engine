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

## Update (2026-06-27): the gate also verifies the loader is actually served

The "tag present still over-qualifies" limitation above turned out to dominate: on a random
sample of 40 real Tidio-tagged stores, 17 passed the tag gate but only 3 delivered - the other
~70% returned `no_tidio_api`, and a diagnosis (production path, frozen sample) showed their
`code.tidio.co/<key>.js` loader returns **403/404**: the static tag lingers in the HTML long
after the store's Tidio account expires or is removed. So the gate now also GETs the loader
during assessment: **200 -> pass; 401/403/404/410 -> Dead `tidio loader dead`; timeout/5xx/
connection-error -> `loader unknown`, which stays Queued/retryable** so a transient blip never
false-kills a live store. This is one cheap HTTP GET per Tidio candidate and it filters the
dead-account stores before any browser launch (~3.5x fewer wasted launches on this sample),
turning the gate from "tag present" into "tag present AND loader live". It does not change the
true deliverable pool, only how cheaply we identify it. Foundation measured, not assumed
(see the hard rule: prove rates on a random sample through the production path).
