# 0002 - Capture replies from one email inbox, not per-vendor

Status: accepted (2026-06-22)

Every chat vendor we target delivers a Brand's reply to the email address we leave at the
chat gate (confirmed across Shopify Inbox, Intercom, Tidio, Gorgias, Tawk.to, and Crisp -
see research/reply-delivery.md). So the Reply Watcher watches that single inbox, rather
than integrating with each vendor's API to read replies.

Why it is recorded here: it is hard to reverse (moving to per-vendor reply polling later
would reshape the Reply Watcher), surprising without context (the intuitive design is a
per-vendor integration), and a real trade-off (one inbox is vendor-agnostic and lets new
Adapters ship without touching the reply side, but it depends on the email-back path and
cannot see a reply that stays only inside a widget). This ADR stops future work from
building per-vendor reply tracking.
