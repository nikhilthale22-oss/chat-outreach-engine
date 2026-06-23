# Research: how a Brand reply reaches us (resolved 2026-06-22)

The Phase-0 research-interrupt on reply capture. Doc-grounded, each finding
adversarially verified against the vendor's official help center.

## Question
We inject a Pitch into a Brand's Chat Widget, leave our email, and close the tab.
When the Brand's agent replies, does it reach our email?

## Answer: YES across all 6 top vendors (we leave an email + we are offline = email-back path)

| Vendor | Reaches our email? | Mechanism | Conditions | Source |
|---|---|---|---|---|
| Shopify Inbox | YES (auto, no toggle) | When visitor offline, reply is emailed to the address given at chat start | email captured (default prompt); visitor offline | help.shopify.com/en/manual/inbox/conversations |
| Intercom | YES (auto, default) | Emails the reply on visitor inactivity; visitor can reply back into the thread | Intercom has an email for the contact | intercom.com/help article 3527623 |
| Tidio | YES (auto, no plan gate) | Auto-emails unread messages + transcript ~15 min after visitor leaves | email captured; visitor left with unread msg | help.tidio.com article 5463385056284 |
| Gorgias | CONDITIONAL | Offline-capture creates an email thread; agent reply continues over email | chat in OFFLINE mode (off-hours / no agents); if AI-Agent-for-chat is on, AI handles instead (but those are skipped anyway) | docs.gorgias.com/en-US/offline-capture-88573 |
| Tawk.to | CONDITIONAL | Agent must convert the offline message to a Ticket; then reply is emailed | ticketing enabled; valid email captured; agent clicks Create Ticket | help.tawk.to responding-to-offline-messages-via-ticketing |
| Crisp | CONDITIONAL | Emails a transcript ~1hr after close/stalled, or agent sends on demand | "Email users transcripts" setting on; email captured | help.crisp.chat article 123u31k |

## Two build implications
1. **Reply Watcher = one inbox, not N integrations.** Every vendor routes replies to
   email, so reply capture is a single watcher on the Gmail we leave at the gate
   (nikhilthale18@gmail.com today). Adding a vendor only needs a new send Adapter; the
   reply side is unchanged. Major de-risk for multi-vendor scaling.
2. **Pitch off-hours.** The email-back path is triggered by the visitor/chat being
   offline. Pitching outside the Brand's business hours maximizes reply delivery,
   especially for Gorgias (live mode does not document emailing an abandoned session).

## Confidence
High for Shopify Inbox, Intercom, Tidio, Gorgias, Tawk. Medium for Crisp (transcript
setting default state not documented). All verified against official docs.
