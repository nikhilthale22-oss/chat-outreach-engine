"""ReplyWatcher: watch one inbox and mark a Brand Replied when its merchant replies.

Per ADR-0002 every chat vendor emails a Brand's reply to the address we leave at the gate, so
we poll one Gmail inbox and match each new message back to a Pitched Brand. The fetch step is
injected (the live one uses stdlib imaplib over an app password) so the match + Ledger logic is
testable without a real inbox. The match heuristic is deliberately simple and will be refined
once we see a real reply's actual shape (which vendor sends it, what the From/Subject look like).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Email:
    from_addr: str
    subject: str
    body: str
    uid: str = ""


# Strong, specific markers of an automated reply (CSAT surveys, vacation responders, no-reply
# senders). Kept deliberately tight: a genuine human "yes, interested" is the precious signal,
# so we only drop on unambiguous auto-reply phrasing, never on a generic word like "feedback".
# Seeded from the first real reply we got (glamnetic's Gorgias CSAT). See ADR-0002 / #12.
_AUTO_REPLY_MARKERS = (
    "rate our service",
    "click on the stars",
    "how did we do",
    "out of office",
    "automatic reply",
    "auto-reply",
    "autoreply",
    "automated response",
    "this is an automated",
    "do not reply to this",
    "please do not reply",
)
# NB: we deliberately do NOT filter on a no-reply *sender*. The legitimate Tidio reply
# notification itself arrives from a no-reply system address (e.g. noreply@tidio.email,
# "New message from <Brand>"), so a sender-based filter would drop the very replies we want.
# Auto-replies are caught by their body/subject phrasing instead.


def is_auto_reply(email: Email) -> bool:
    """True if this looks like an automated message (CSAT survey, vacation responder), which
    must not be counted as a real merchant reply. Judged by body/subject text, not sender."""
    text = f"{email.subject}\n{email.body}".lower()
    return any(m in text for m in _AUTO_REPLY_MARKERS)


def default_matcher(email: Email, pitched_domains) -> str | None:
    """Return the Pitched domain this reply belongs to, or None. Heuristic: the domain (or its
    bare brand token) appears in the From, Subject, or body. Longest domain wins so a more
    specific host (shop.foo.com) beats a generic one (foo.com). Automated messages (CSAT, OOO,
    no-reply) are never matched - they are noise, not a real reply."""
    if is_auto_reply(email):
        return None
    hay = f"{email.from_addr}\n{email.subject}\n{email.body}".lower()
    for d in sorted(pitched_domains, key=len, reverse=True):
        dl = d.lower()
        if dl in hay:
            return d
        brand = dl.split(".")[0].removeprefix("www").strip(".-")
        if len(brand) >= 4 and brand in hay:
            return d
    return None


class ReplyWatcher:
    def __init__(self, ledger, fetch_unseen, matcher=default_matcher, on_event=None):
        self._ledger = ledger
        self._fetch_unseen = fetch_unseen          # () -> list[Email]
        self._matcher = matcher
        self._on_event = on_event or (lambda m: None)

    def poll(self) -> list:
        """Fetch new messages, advance any that match a Pitched Brand to Replied, and return
        a list of (Email, matched_domain_or_None). Idempotent per Brand: once a Brand is
        Replied it is no longer in the Pitched set, so a second email won't re-advance it."""
        pitched = set(self._ledger.list_by_stage("Pitched"))
        results = []
        for email in self._fetch_unseen():
            domain = self._matcher(email, pitched)
            if domain and domain in pitched:
                self._ledger.advance(domain, "Replied", note=f"reply from {email.from_addr}")
                pitched.discard(domain)
                results.append((email, domain))
                self._on_event(f"REPLIED: {domain} <- {email.from_addr}")
            else:
                results.append((email, None))
                self._on_event(f"unmatched: {email.from_addr} | {email.subject[:60]}")
        return results


def imap_fetch_unseen(host: str, user: str, password: str, mailbox: str = "INBOX"):
    """Build a fetch_unseen() that pulls UNSEEN messages from a Gmail inbox over IMAP SSL.
    Marks them seen by virtue of the RFC822 fetch. Lazy imports so the package imports without
    a live inbox in tests."""
    def fetch() -> list:
        import email as emaillib
        import imaplib

        out = []
        m = imaplib.IMAP4_SSL(host)
        try:
            m.login(user, password)
            m.select(mailbox)
            _, data = m.search(None, "UNSEEN")
            for uid in (data[0].split() if data and data[0] else []):
                _, msgdata = m.fetch(uid, "(RFC822)")
                if not msgdata or not msgdata[0]:
                    continue
                msg = emaillib.message_from_bytes(msgdata[0][1])
                out.append(Email(
                    from_addr=str(msg.get("From", "")),
                    subject=str(msg.get("Subject", "")),
                    body=_extract_body(msg),
                    uid=uid.decode(),
                ))
        finally:
            try:
                m.logout()
            except Exception:
                pass
        return out

    return fetch


def _extract_body(msg) -> str:
    """Best-effort plain-text body."""
    try:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode(part.get_content_charset() or "utf-8", "ignore")
            return ""
        payload = msg.get_payload(decode=True)
        return payload.decode(msg.get_content_charset() or "utf-8", "ignore") if payload else ""
    except Exception:
        return ""
