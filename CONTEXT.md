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
