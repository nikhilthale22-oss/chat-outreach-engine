# 0001 - Chat-widget injection only, never cold email

Status: accepted (2026-06-22)

We pitch brands only by injecting a message into their own live chat widget. We do not use
cold email as a channel, and we do not revisit this. Volume grows by supporting more chat
vendors, never by adding email sending capacity.

Why it is recorded here: it is hard to reverse (the whole architecture and skillset is
built around chat injection, not deliverability infra), surprising without context (cold
email is the obvious high-volume outbound default, so reviews will keep proposing it), and
a real trade-off (we trade email's raw ceiling for a higher-attention, less-commoditized
channel we believe in). This ADR exists to stop every future plan from re-suggesting
"just scale cold email."
