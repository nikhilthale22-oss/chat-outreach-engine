"""The Pipeline: one unit that runs on any store. detect -> route -> send.

A domain goes in; a PipelineResult comes out. Same three steps on every store; only the
per-vendor adapter (the "card") changes. This is the machine Nikhil described - "a single
process that follows a set of steps ... the whole process as a unit functions no matter what":

  1. detect - which chat vendor (static homepage fingerprint)         -> Detection
  2. route  - vendor -> a send method, or skip (no widget / gated /    -> Route
              no method we support)
  3. send   - dispatch a `headed`-routed store to its browser adapter  -> SendResult

Skips are first-class OUTCOMES, never errors: the machine always RUNS on any store; it only
DELIVERS where a card exists. API/form methods are parked (ADR-0008, all-headed), so a store
that would route to them is reported unsupported, not sent.

Relationship to batch.py: this is the per-store UNIT. batch.py is the concurrency wrapper (the
volume engine) and today still walks detect/route/send inline with an extra live-loader gate;
folding batch onto this unit is a later reshape step. Use Pipeline for a single store or a
small, sequential proof run.
"""
from __future__ import annotations

from dataclasses import dataclass

from .detect import SignatureDetector
from .route import registry
from .route.router import route as route_detection
from .send.headed import build_headed_adapters

DEFAULT_REPLY_EMAIL = "nikhilmercwise@zohomail.in"


@dataclass(frozen=True)
class PipelineResult:
    domain: str
    action: str                 # "sent" | "failed" | "skipped" | "would_send"
    reason: str                 # route reason ("gated"/"no_widget"/...) or "dry_run" preview
    vendor: str | None = None
    method: str | None = None   # the routed method once a send is reached
    detail: str | None = None   # adapter SendResult.detail when a send was attempted


class Pipeline:
    """detect -> route -> send, composed. The detector and the adapter map are injectable so tests
    can drive it with no network and no browser, and the live proof can pass the real
    SignatureDetector + the headed adapters."""

    def __init__(self, detector=None, adapters=None, reply_email: str = DEFAULT_REPLY_EMAIL):
        self._detector = detector or SignatureDetector()
        self._adapters = adapters if adapters is not None else build_headed_adapters()
        self._reply_email = reply_email

    def run_one(self, domain: str, pitch: str, dry_run: bool = False) -> PipelineResult:
        """Run one store through the whole unit. dry_run stops after routing (no browser) so a list
        can be previewed for free - which stores WOULD send, and where every skip falls out."""
        domain = (domain or "").strip().lower()

        detection = self._detector.detect(domain)
        decision = route_detection(detection)

        if decision.action == "skip":
            return PipelineResult(domain, "skipped", decision.reason, detection.vendor)

        method = decision.method
        if method != registry.METHOD_HEADED:
            # Routed to a real method, but api/form are parked (ADR-0008). Reachable in principle,
            # no active card - report it, never silently drop it.
            return PipelineResult(domain, "skipped", f"method_parked:{method}",
                                  detection.vendor, method)

        adapter = self._adapters.get(detection.vendor)
        if adapter is None:
            return PipelineResult(domain, "skipped", "no_adapter", detection.vendor, method)

        if dry_run:
            return PipelineResult(domain, "would_send", "dry_run", detection.vendor, method)

        result = adapter.send(domain, pitch, self._reply_email)
        action = "sent" if result.sent else "failed"
        return PipelineResult(domain, action, decision.reason, detection.vendor, method,
                              result.detail)


__all__ = ["Pipeline", "PipelineResult", "DEFAULT_REPLY_EMAIL"]
