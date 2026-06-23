# Research: Tidio injection (#8) - 2026-06-23 (REVISED after deep frame inspection)

Tidio is the chosen pivot vendor after Shopify Inbox turned out CAPTCHA-walled.

## The real finding: it's a clean JS-API vendor, NOT a DOM-driving one

The first-cut adapter tried to open the Tidio panel and type into a composer textarea.
A deep live frame-inspection pass (/tmp/tidio_inspect*.py, /tmp/tidio_api_probe.py) proved
that was a dead end and found the correct path:

1. **Tidio's chat PANEL does not render under Playwright automation.** Calling
   `tidioChatApi.open()` does not create the chat-window iframe / composer (confirmed on
   talleyandtwine.com: after open(), zero tidio iframes, no textarea). So there is no
   composer to type into. Every "no_composer" failure was this, not a popup/overlay problem.
2. **The JS API IS fully available once the widget loads.** On a store that loads Tidio,
   `window.tidioChatApi.readyEventWasFired === true` and the API exposes exactly what we need:
   `messageFromVisitor(text)` (sends a message AS the visitor), `setContactProperties({email})`
   and `setVisitorData({distinct_id,email})` (attach the reply email so the operator's reply
   routes back per ADR-0002), plus open/close/display/show/track. **No CAPTCHA.**
3. So the adapter is now the SAME shape as Gorgias: load page -> wait for the API + ready
   event -> set the contact email -> `messageFromVisitor(pitch)`. No panel, no composer,
   no popup-dismissal needed.

## Which Tidio stores load under automation (important coverage caveat)

Re-checking static HTML (curl) for the real loader is the gate:
- **Direct script tag** `code.tidio.co/<id>.js` in the HTML -> the API initialises under
  headless automation. **Automatable.** (talleyandtwine.com: API present + ready + all methods.)
- **Dynamic embed** (only `tidioChatApi` referenced, injected by a Shopify app embed / GTM,
  no direct code.tidio.co tag) -> the loader does NOT fire under automation, headless OR
  headed. API never appears -> adapter returns `no_tidio_api` (correctly Queued, retryable).
  (mulberryparksilks.com: tidioChatApi referenced in HTML but never loads in Playwright.)
- The /tmp/tidio_live.json scan also had **false positives** (ninjatransfers.com has NO Tidio
  in its HTML at all - the visible textarea there is the site's own AI image editor). The
  batch runner must re-confirm `code.tidio.co/<id>.js` in the live HTML before counting a
  store as a Tidio target, else coverage numbers are inflated.

## Adapter status (adapters/tidio.py) - REWRITTEN to the API path
Done: goto -> poll for `tidioChatApi.readyEventWasFired` (<=25s) -> setContactProperties +
setVisitorData with reply_email -> open() to init the session -> `messageFromVisitor(pitch)`.
Returns `pitch_sent_via_api` on success, `no_tidio_api` if the widget never loads.

Proven so far (no spam sent):
- talleyandtwine.com: API present, readyEventWasFired=True, messageFromVisitor/setContact*/
  setVisitorData/open all present (tidio_api_probe.py).
- CLI dry-run: talleyandtwine.com -> detected vendor=tidio -> qualified -> routed to
  TidioAdapter -> dry_run (Ledger=Queued). Full pipeline works end to end up to the send.

## The one remaining step = HITL live-verify (standing rule: live pitch to a real brand)
`messageFromVisitor` delivery to the operator inbox + reply routing to the gate email cannot
be confirmed without one real send to a real store. That is Nikhil's go (same as the Gorgias
glamnetic/iheartraves sends). Run: `python -m chat_outreach_engine.cli talleyandtwine.com
--send --email nikhilthale18@gmail.com` (optionally HEADED=1). Then confirm it lands in the
store's Tidio inbox and the reply comes back to the gate email.

## Test stores (re-verified real Tidio via direct script tag)
talleyandtwine.com (cleanest, API loads instantly). shoshanna.com (real, but consent-gated:
Tidio loads only after cookie-consent is accepted). 40 candidates in /tmp/tidio_live.json but
that list needs the code.tidio.co re-check (ninjatransfers.com was a false positive).
