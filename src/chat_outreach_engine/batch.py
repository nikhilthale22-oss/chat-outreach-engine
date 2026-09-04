"""BatchRunner: pitch a list of Brands concurrently. The volume engine.

Concurrency model (so the Ledger's single SQLite connection is only ever touched from the
calling thread): the slow network steps - live Assessment (one HTTP fetch per Brand) and the
browser Pitch send - run in a thread pool; every Ledger read/write happens serially in run().

Phases:
  0. Skip Brands the Ledger already moved past Queued (resumable, and we don't re-fetch them).
  1. Assess the rest concurrently: one fetch -> vendor + has_ai + a LIVE re-verify gate.
  2. Serially decide each Brand (Ledger): Dead (no widget / has AI / gate failed / no adapter),
     left Queued (transient fetch failure, retryable), or queued to send with an A/B variant.
  3. Send the worklist concurrently through the per-vendor Adapters (no Ledger access).
  4. Serially record each result: mark_pitched(variant) on a confirmed send, else leave Queued.

The LIVE re-verify gate matters: the static scan has false positives and (for Tidio) dynamic
Shopify-app-embed stores that never initialise under automation - we must confirm the real
loader against the live HTML before spending a browser launch.
"""
from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from .detect import signatures
from .ledger import Ledger, UnknownBrand
from .pitches import PITCHES

AI_CATEGORY = "ai-chat"
# Adapter SendResult.detail values that are STRUCTURALLY terminal (will never deliver on a retry,
# OR must never be retried because a retry could double-send), so the Brand is marked Dead instead
# of re-launching a browser at it forever. Transient details (no_tidio_api, no_composer, timeouts)
# stay retryable and are bounded by the attempt cap instead.
#   prechat_blocked_required_fields - required fields we cannot satisfy block the send (held).
#   captcha_challenge               - Shopify Inbox passive hCaptcha showed a visible challenge.
#   submitted_unconfirmed           - Shopify Inbox: form GONE + Start chat clicked + no render = the
#                                     message genuinely COMMITTED but unconfirmable; terminal so a retry
#                                     can never double-send a real merchant. Honest: not marked pitched
#                                     (we are not sure), but never re-attempted (we might have).
# NOTE: form_blocked is NOT terminal. The 75-store run proved (SI_DEBUG dumps) that a Shopify Inbox
# contact form STILL VISIBLE after our click means the submission was silently rejected and NOTHING was
# posted - so it is RETRYABLE (re-pitch cannot double-send what never sent). Marking it terminal burned
# ~20 re-pitchable stores as Dead. The attempt cap still bounds the retries.
TERMINAL_SEND_DETAILS = {"prechat_blocked_required_fields",
                         "captcha_challenge", "submitted_unconfirmed"}
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")


@dataclass(frozen=True)
class Assessment:
    domain: str
    fetched: bool          # did we get HTML at all (False = transient, retryable)
    has_widget: bool
    vendor: str | None
    has_ai: bool
    gate_passed: bool       # live re-verify: this vendor will really load under automation
    gate_reason: str | None = None  # why the gate failed (distinguishes dead vs retryable)


@dataclass(frozen=True)
class Outcome:
    domain: str
    action: str            # pitched | send_failed | dead | skipped | fetch_failed | would_pitch
    reason: str
    vendor: str | None = None
    variant: str | None = None


@dataclass
class BatchReport:
    outcomes: list = field(default_factory=list)

    def add(self, o: Outcome) -> None:
        self.outcomes.append(o)

    @property
    def counts(self) -> dict:
        c: dict = {}
        for o in self.outcomes:
            c[o.action] = c.get(o.action, 0) + 1
        return c

    @property
    def pitched(self) -> list:
        return [o for o in self.outcomes if o.action == "pitched"]

    def summary(self) -> str:
        c = self.counts
        parts = [f"{k}={v}" for k, v in sorted(c.items())]
        va = sum(1 for o in self.pitched if o.variant == "A")
        vb = sum(1 for o in self.pitched if o.variant == "B")
        return f"{len(self.outcomes)} brands | " + " ".join(parts) + f" | pitched A={va} B={vb}"


def live_gate(vendor: str | None, html: str) -> bool:
    """Confirm, against the live HTML, that this vendor's widget will actually load under
    automation. Tidio: require a DIRECT code.tidio.co/<id>.js loader tag; Tawk: a direct
    embed.tawk.to/<pid>/<wid> loader tag (dynamic app-embed / deferred-injection stores only
    reference the runtime global and never initialise headless). Other automatable vendors: the
    static signature already implies a loadable widget."""
    if not html:
        return False
    if vendor == "tidio":
        return bool(re.search(r"code\.tidio\.co/[a-z0-9]+\.js", html, re.I))
    if vendor == "tawk.to":
        return bool(re.search(r"embed\.tawk\.to/[0-9a-fA-F]{16,}/[0-9A-Za-z]+", html, re.I))
    if vendor == "zendesk":
        return bool(re.search(r"static\.zdassets\.com/ekr/snippet\.js\?key=", html, re.I))
    return True


# Loader-liveness states. The static tag can linger in a store's HTML long after its Tidio
# account expires (the loader then 403s), so passing the gate also requires the loader to be
# actually served. UNKNOWN is deliberately NOT dead - a transient blip must never false-kill
# a live store (it stays retryable, like a failed homepage fetch).
LOADER_LIVE = "live"
LOADER_DEAD = "dead"
LOADER_UNKNOWN = "unknown"


def _tidio_loader_url(html: str) -> str | None:
    """The full https URL of Tidio's widget loader in this HTML, or None. Forces https so the
    common protocol-relative `//code.tidio.co/<key>.js` form is fetchable."""
    if not html:
        return None
    m = re.search(r"code\.tidio\.co/[a-z0-9]+\.js", html, re.I)
    return ("https://" + m.group(0)) if m else None


def _tawk_loader_url(html: str) -> str | None:
    """The full https URL of Tawk's widget loader (embed.tawk.to/<propertyId>/<widgetId>), or None.
    The static tag lingers after a Tawk account expires (the loader then 403/404s), same as Tidio."""
    if not html:
        return None
    m = re.search(r"embed\.tawk\.to/[0-9a-fA-F]{16,}/[0-9A-Za-z]+", html, re.I)
    return ("https://" + m.group(0)) if m else None


def _zendesk_loader_url(html: str) -> str | None:
    """The full https URL of Zendesk's widget loader (static.zdassets.com/ekr/snippet.js?key=<uuid>),
    or None. The snippet tag lingers in a store's HTML after its Zendesk account lapses (the loader
    then 40x's) and the static signature also matches stores that have since dropped Zendesk, so the
    loader GET filters both - only a 200 means the widget will actually initialise (no_zendesk_api)."""
    if not html:
        return None
    m = re.search(r"static\.zdassets\.com/ekr/snippet\.js\?key=[0-9a-fA-F-]{8,}", html, re.I)
    return ("https://" + m.group(0)) if m else None


def _loader_url(vendor: str | None, html: str) -> str | None:
    """The widget-loader URL whose liveness we re-verify for this vendor, or None for vendors that
    have no dead-account-lingering-tag problem (so no loader GET is spent on them)."""
    if vendor == "tidio":
        return _tidio_loader_url(html)
    if vendor == "tawk.to":
        return _tawk_loader_url(html)
    if vendor == "zendesk":
        return _zendesk_loader_url(html)
    return None


def loader_liveness(url: str | None, fetch=None) -> str:
    """Is the widget loader actually being served? GET it (following redirects): 200 -> LIVE;
    401/403/404/410 (suspended / expired / removed account) -> DEAD; timeout, 5xx, or any
    connection error -> UNKNOWN (retryable, never treated as dead)."""
    if not url:
        return LOADER_UNKNOWN
    fetch = fetch or _loader_http_status
    try:
        status = fetch(url)
    except Exception:
        return LOADER_UNKNOWN
    if status == 200:
        return LOADER_LIVE
    if status in (401, 403, 404, 410):
        return LOADER_DEAD
    return LOADER_UNKNOWN


def _loader_http_status(url: str) -> int:
    import requests
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    r = requests.get(url, timeout=8, allow_redirects=True, verify=False,
                     headers={"User-Agent": _UA})
    return r.status_code


# Reach robustness for the FREE (no-proxy) path. A single datacenter IP mostly gets HTTP 429
# (rate limited) in bursts, not banned - so a short backoff recovers the store instead of losing
# it. Before this, a 429 error PAGE was returned as if it were the storefront, matched no widget
# signature, and the Brand was marked Dead: silently burning reachable stores. Now a rate-limit
# backs off and retries, and a persistent block returns "" (a RETRYABLE fetch_failed that leaves
# the Brand Queued for a later run - or another shard's IP - never a false "no widget" Dead).
_FETCH_ATTEMPTS = 3


def _is_retryable_status(status: int) -> bool:
    """HTTP statuses worth retrying the SAME fetch after a backoff: 429 (rate limited) and 5xx
    (transient server/edge errors). 4xx like 403/404 are not retried here (they leave the Brand
    Queued via an empty result, so a later run from a fresh IP can still pick them up)."""
    return status == 429 or 500 <= status <= 599


def _backoff_seconds(attempt: int, base: float = 0.5, cap: float = 8.0) -> float:
    """Exponential backoff for a 0-indexed retry attempt: 0.5s, 1s, 2s, 4s ... capped at `cap`."""
    return min(cap, base * (2 ** attempt))


def fetch_html(domain: str, get=None, sleep=None, attempts: int = _FETCH_ATTEMPTS) -> str:
    """Fetch a Brand's homepage HTML, retrying rate-limits/5xx with backoff. Returns the page text
    on a 2xx, else "" (empty = a RETRYABLE fetch_failed at the batch level, never a false Dead).
    `get(url) -> (status, text)` and `sleep(secs)` are injectable so the retry policy is unit-tested
    without real HTTP; the defaults use requests (honoring the opt-in proxy) + time.sleep."""
    get = get or _http_get
    sleep = sleep or time.sleep
    for scheme in ("https://", "http://"):
        for attempt in range(attempts):
            try:
                status, text = get(scheme + domain)
            except Exception:
                break                      # connection error on this scheme -> try the other scheme
            if 200 <= status < 300:
                return (text or "")[:2_000_000]
            if _is_retryable_status(status) and attempt < attempts - 1:
                sleep(_backoff_seconds(attempt))
                continue
            break                          # non-retryable status or attempts exhausted
    return ""


def _http_get(url: str):
    import requests
    import urllib3

    from .proxy import requests_proxies

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    headers = {"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"}
    r = requests.get(url, headers=headers, timeout=15, verify=False,
                     allow_redirects=True, proxies=requests_proxies())
    return r.status_code, (r.text or "")


class LiveAssessor:
    """Fetches a Brand's homepage ONCE and derives vendor + has_ai + the live gate. For Tidio
    the gate also verifies the loader is actually live (filters expired/removed accounts whose
    static tag still lingers in the HTML). Both fetches are injectable for testing."""

    def __init__(self, fetch=None, loader_fetch=None) -> None:
        signatures.compile_patterns()
        self._fetch_fn = fetch or self._fetch
        self._loader_fetch = loader_fetch   # None -> real HTTP GET of the loader

    def __call__(self, domain: str) -> Assessment:
        html = self._fetch_fn(domain)
        if not html:
            return Assessment(domain, False, False, None, False, False)
        hits = signatures.match_html(html)
        if not hits:
            return Assessment(domain, True, False, None, False, False)
        vendor = hits[0]["vendor"]
        has_ai = any(h.get("category") == AI_CATEGORY for h in hits)
        if not live_gate(vendor, html):
            return Assessment(domain, True, True, vendor, has_ai, False)
        loader = _loader_url(vendor, html)
        if loader is not None:
            state = loader_liveness(loader, fetch=self._loader_fetch)
            if state == LOADER_DEAD:
                return Assessment(domain, True, True, vendor, has_ai, False, f"{vendor} loader dead")
            if state == LOADER_UNKNOWN:
                return Assessment(domain, True, True, vendor, has_ai, False, "loader unknown")
        return Assessment(domain, True, True, vendor, has_ai, True)

    @staticmethod
    def _fetch(domain: str) -> str:
        return fetch_html(domain)


class ForcedVendorAssessor:
    """Assessor for a KNOWN-vendor list: routes every domain straight to one vendor's Adapter, skipping
    static signature detection. Needed for Shopify Inbox - its script injects via JS, so the static
    SignatureDetector never sees it and the normal path would mark every SI store "no chat widget" and
    Dead before the adapter runs. The adapter does its OWN browser-layer liveness check (returns
    no_shopify_inbox when the widget is not actually present), so a stale list entry fails safe at send.
    has_ai is taken as False (these widgets are human chat by default; the no-AI offer framing is the
    only risk, accepted for a pre-filtered list). Use only when the input list is already one vendor."""

    def __init__(self, vendor: str):
        self._vendor = vendor

    def __call__(self, domain: str) -> Assessment:
        return Assessment(domain, True, True, self._vendor, False, True)


class BatchRunner:
    def __init__(self, ledger: Ledger, adapters: dict, reply_email: str,
                 assessor=None, pitches: dict | None = None, concurrency: int = 8,
                 assess_concurrency: int = 16, max_attempts: int = 4, on_event=None):
        self._ledger = ledger
        self._adapters = adapters
        self._reply_email = reply_email
        self._assessor = assessor or LiveAssessor()
        self._pitches = pitches or PITCHES
        self._concurrency = max(1, concurrency)
        # Assessment is lightweight HTTP, so it runs at a higher concurrency than the
        # browser sends (which are memory-bound). Otherwise assessing thousands of stores
        # at the send concurrency would delay the first pitch by hours.
        self._assess_concurrency = max(1, assess_concurrency)
        self._max_attempts = max(1, max_attempts)
        self._on_event = on_event or (lambda msg: None)

    def run(self, domains, dry_run: bool = False, limit: int | None = None) -> BatchReport:
        report = BatchReport()
        seen: set = set()
        clean = []
        for d in domains:
            d = (d or "").strip().lower()
            if not d or d in seen:
                continue
            seen.add(d)
            clean.append(d)

        # Phase 0: drop Brands already past Queued (serial Ledger reads; keeps us from re-fetching).
        to_assess = []
        for d in clean:
            stage = self._stage_or_none(d)
            if stage is not None and stage != "Queued":
                report.add(Outcome(d, "skipped", f"already {stage}"))
            else:
                to_assess.append(d)
        # Apply --limit to FRESH work, not the raw list, so a resumed run is not consumed by
        # already-done Brands at the top of the file.
        if limit is not None:
            to_assess = to_assess[:limit]
        self._on_event(f"assessing {len(to_assess)} brands "
                       f"({len(clean) - len(to_assess)} skipped/done)")

        # Phase 1: concurrent live assessment (high concurrency - it's just HTTP).
        assessments = self._map(self._safe_assess, to_assess, workers=self._assess_concurrency)

        # Phase 2: serial Ledger decisions -> send worklist.
        worklist = []  # (domain, vendor, variant)
        vi = 0
        for a in assessments:
            self._ledger.add_brand(a.domain, vendor=a.vendor)
            if not a.fetched:
                report.add(Outcome(a.domain, "fetch_failed", "no HTML (retryable)", a.vendor))
                continue
            if not a.has_widget:
                self._ledger.advance(a.domain, "Dead", note="no chat widget")
                report.add(Outcome(a.domain, "dead", "no chat widget"))
                continue
            if a.has_ai:
                self._ledger.advance(a.domain, "Dead", note="already has AI")
                report.add(Outcome(a.domain, "dead", "already has AI", a.vendor))
                continue
            if not a.gate_passed:
                if a.gate_reason == "loader unknown":
                    # transient loader check - leave Queued (retryable), never kill a maybe-live store
                    report.add(Outcome(a.domain, "loader_unknown",
                                       "loader liveness unknown (retryable)", a.vendor))
                    continue
                reason = a.gate_reason or "live re-verify failed"
                self._ledger.advance(a.domain, "Dead", note=reason)
                report.add(Outcome(a.domain, "dead", reason, a.vendor))
                continue
            if a.vendor not in self._adapters:
                self._ledger.advance(a.domain, "Dead", note=f"no adapter for {a.vendor}")
                report.add(Outcome(a.domain, "dead", f"no adapter for {a.vendor}", a.vendor))
                continue
            variant = "A" if vi % 2 == 0 else "B"
            vi += 1
            worklist.append((a.domain, a.vendor, variant))

        if dry_run:
            for domain, vendor, variant in worklist:
                report.add(Outcome(domain, "would_pitch", "qualified (dry run)", vendor, variant))
            self._on_event(report.summary())
            return report

        self._on_event(f"sending {len(worklist)} pitches "
                       f"(concurrency {self._concurrency})")

        # Phase 3+4 fused: send concurrently, but RECORD each result to the Ledger the moment
        # its send returns (on the main thread, so the single SQLite connection stays single-
        # threaded). This shrinks the double-send window from the whole batch to one in-flight
        # send: a crash/Ctrl-C can only lose pitches still on the wire, not already-confirmed
        # ones. The finally drains any sends that completed during shutdown (e.g. a Ctrl-C that
        # lets in-flight browsers finish) so those are recorded too, not silently re-pitched.
        if worklist:
            workers = min(self._concurrency, len(worklist))
            recorded: set = set()
            ex = ThreadPoolExecutor(max_workers=workers)
            futures = {ex.submit(self._safe_send, item): item for item in worklist}
            try:
                for fut in as_completed(futures):
                    self._record_send(fut.result(), report)
                    recorded.add(fut)
            finally:
                ex.shutdown(wait=True)
                for fut in futures:
                    if fut not in recorded and fut.done() and not fut.cancelled():
                        try:
                            self._record_send(fut.result(), report)
                            recorded.add(fut)
                        except Exception:
                            pass

        self._on_event(report.summary())
        return report

    def _record_send(self, result, report) -> None:
        domain, vendor, variant, sent, detail = result
        if sent:
            self._ledger.mark_pitched(domain, pitch_variant=variant)
            report.add(Outcome(domain, "pitched", detail, vendor, variant))
        elif detail in TERMINAL_SEND_DETAILS:
            self._ledger.advance(domain, "Dead", note=detail)
            report.add(Outcome(domain, "dead", detail, vendor, variant))
        else:
            n = self._ledger.record_send_failure(domain, detail)
            if n >= self._max_attempts:
                self._ledger.advance(domain, "Dead", note=f"unreachable after {n} attempts")
                report.add(Outcome(domain, "dead", f"unreachable after {n} attempts",
                                   vendor, variant))
            else:
                report.add(Outcome(domain, "send_failed", detail, vendor, variant))
        self._on_event(f"{domain}: {report.outcomes[-1].action} ({variant}) {detail}")

    # --- helpers ---
    def _map(self, fn, items, workers=None):
        if not items:
            return []
        workers = min(workers or self._concurrency, len(items))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            return list(ex.map(fn, items))

    def _safe_assess(self, domain: str) -> Assessment:
        try:
            return self._assessor(domain)
        except Exception:
            return Assessment(domain, False, False, None, False, False)

    def _safe_send(self, item):
        domain, vendor, variant = item
        pitch = self._pitches.get(variant) or self._pitches["A"]
        try:
            res = self._adapters[vendor].send(domain, pitch, self._reply_email)
            return (domain, vendor, variant, bool(res.sent), res.detail)
        except Exception as e:
            return (domain, vendor, variant, False, f"{type(e).__name__}: {str(e)[:140]}")

    def _stage_or_none(self, domain: str):
        try:
            return self._ledger.get_stage(domain)
        except UnknownBrand:
            return None
