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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from . import signatures
from .ledger import Ledger, UnknownBrand
from .pitches import PITCHES

AI_CATEGORY = "ai-chat"
# Adapter SendResult.detail values that are STRUCTURALLY terminal (will never deliver on a
# retry), so the Brand is marked Dead instead of re-launching a browser at it forever. Only
# the documented-terminal one; transient details (no_tidio_api, no_composer, timeouts) stay
# retryable and are bounded by the attempt cap instead.
TERMINAL_SEND_DETAILS = {"prechat_blocked_required_fields"}
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
    automation. Tidio: require a DIRECT code.tidio.co/<id>.js loader tag (dynamic app-embed
    stores only reference tidioChatApi and never initialise headless). Other automatable
    vendors: the static signature already implies a loadable widget."""
    if not html:
        return False
    if vendor == "tidio":
        return bool(re.search(r"code\.tidio\.co/[a-z0-9]+\.js", html, re.I))
    return True


class LiveAssessor:
    """Fetches a Brand's homepage ONCE and derives vendor + has_ai + the live gate."""

    def __init__(self) -> None:
        signatures.compile_patterns()

    def __call__(self, domain: str) -> Assessment:
        html = self._fetch(domain)
        if not html:
            return Assessment(domain, False, False, None, False, False)
        hits = signatures.match_html(html)
        if not hits:
            return Assessment(domain, True, False, None, False, False)
        vendor = hits[0]["vendor"]
        has_ai = any(h.get("category") == AI_CATEGORY for h in hits)
        return Assessment(domain, True, True, vendor, has_ai, live_gate(vendor, html))

    @staticmethod
    def _fetch(domain: str) -> str:
        import requests
        import urllib3

        from .proxy import requests_proxies

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        headers = {"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"}
        proxies = requests_proxies()
        for scheme in ("https://", "http://"):
            try:
                r = requests.get(scheme + domain, headers=headers, timeout=15,
                                 verify=False, allow_redirects=True, proxies=proxies)
                return (r.text or "")[:2_000_000]
            except Exception:
                continue
        return ""


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
                self._ledger.advance(a.domain, "Dead", note="live re-verify failed")
                report.add(Outcome(a.domain, "dead", "live re-verify failed", a.vendor))
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
