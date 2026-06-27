# Chat-Outreach Engine

Pitches ecommerce brands inside their own live chat widget, offering to build them an AI
chatbot, and tracks replies through to a booked call.

## Language

> This glossary is seeded with the few unambiguous terms. The grill fills in the rest
> (Channel/Adapter, Qualified, Reply, Ledger, the deployable units) as decisions
> crystallize. Each entry: what the term IS in 1-2 sentences, plus _Avoid_ synonyms.

**Brand**:
An ecommerce store we might pitch. Identified by its domain.
_Avoid_: lead, prospect, target, customer

**Chat Widget**:
The live chat box already installed on a Brand's site (Gorgias, Tidio, Tawk, etc.). The
surface we inject the Pitch into.
_Avoid_: chatbot, chat, widget (bare)

**Pitch**:
The short message we send into a Brand's Chat Widget offering to build them an AI chatbot.
_Avoid_: message, copy, outreach

**Injector**:
The part that pitches one Brand: opens the Brand's site, confirms the Chat Widget and that
there is no AI, then sends the Pitch through the right Adapter.
_Avoid_: bot, sender, script

**Adapter**:
The vendor-specific piece that knows how to drive one kind of Chat Widget (open it, get
past the email box, send the Pitch). One Adapter per vendor.
_Avoid_: connector, plugin, driver

**Reply Watcher**:
The part that notices and records when a Brand replies to a Pitch. Every vendor delivers
replies to the email we leave at the gate, so the Reply Watcher watches one email inbox,
not each vendor separately.
_Avoid_: listener, monitor, poller

**Ledger**:
The running record of every Brand, its current Stage, and its outcome, tagged by vendor
and Pitch variant. Lets us see which vendor and which Pitch actually convert.
_Avoid_: database, log, tracker, CRM

**Stage**:
Where a Brand currently is in the journey. In order: Queued, Pitched, Replied,
Call Booked, Customer (or Dead if it goes nowhere).
_Avoid_: status, state, step

**Qualified**:
A Brand we are allowed to pitch: it has a Chat Widget and no AI behind it. The Injector
confirms this right before sending and skips any Brand that already has AI.
_Avoid_: eligible, valid, target

**Batch Runner**:
The volume engine: takes a list of Brands and pitches them concurrently, doing the slow
network work in parallel while every Ledger write stays serial. Resumable via the Ledger.
_Avoid_: queue, worker pool, job, crawler

**Assessment**:
The result of one live look at a Brand before pitching: did its page load, what vendor its
Chat Widget is, whether it has AI, and whether it passes the Live Re-verify Gate.
_Avoid_: scan, check, detection (bare)

**Live Re-verify Gate**:
The check, against the Brand's live site, that its Chat Widget will actually load under
automation, before a browser launch is spent. For Tidio: a direct code.tidio.co loader tag
(not a dynamic app-embed) AND the loader is actually served - a 200, not the 403/404 a dead
or expired account returns even though its static tag lingers in the HTML. Filters out false
positives, un-loadable stores, and dead accounts cheaply.
_Avoid_: filter, validation, verification (bare)

**Variant**:
Which version of the Pitch a Brand received: A (converts shoppers / CVR) or B (raises average
order value / AOV). Recorded on the Ledger so we can compare which Pitch converts.
_Avoid_: version, arm, test
