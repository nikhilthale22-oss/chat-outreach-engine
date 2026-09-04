"""The Injector: orchestrates pitching one Brand end to end.

Given a Brand domain it asks the Detector for the Chat Widget vendor, confirms the
Brand is Qualified (has a widget, no AI), and if so sends the Pitch through the
vendor's Adapter and records the outcome in the Ledger.

Detection and sending are seams (real implementations hit the network / a browser),
so they are injected and can be faked in tests. The Ledger is our own module and is
used directly, never mocked.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .ledger import Ledger


@dataclass(frozen=True)
class Detection:
    has_widget: bool
    vendor: str | None
    has_ai: bool
    kind: str = "unknown"        # "human" | "ai" | "hybrid" | "unknown"
    category: str | None = None


@dataclass(frozen=True)
class SendResult:
    """What an Adapter reports back: whether the Pitch was sent, plus a short detail."""
    sent: bool
    detail: str = ""


@dataclass(frozen=True)
class Outcome:
    domain: str
    action: str  # "pitched" | "skipped" | "dry_run" | "send_failed"
    reason: str
    vendor: str | None = None


class Detector(Protocol):
    def detect(self, domain: str) -> Detection: ...


class Adapter(Protocol):
    """The one contract every vendor Adapter implements. Given a known Brand domain,
    open that vendor's Chat Widget, pass the email gate with reply_email, send the
    Pitch, and return a SendResult. Adding a vendor means adding one class with this
    single method and registering it; nothing else in the engine changes."""

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult: ...


class Injector:
    def __init__(self, ledger: Ledger, detector: Detector, adapters: dict[str, Adapter]):
        self._ledger = ledger
        self._detector = detector
        self._adapters = adapters

    def process(self, domain: str, pitch: str, reply_email: str,
                pitch_variant: str = "A", dry_run: bool = False) -> Outcome:
        det = self._detector.detect(domain)
        self._ledger.add_brand(domain, vendor=det.vendor)

        if not self._ledger.can_pitch(domain):
            return Outcome(domain, "skipped", "already past Queued", det.vendor)

        if not det.has_widget:
            self._ledger.advance(domain, "Dead", note="no chat widget")
            return Outcome(domain, "skipped", "no chat widget", det.vendor)

        if det.has_ai:
            self._ledger.advance(domain, "Dead", note="already has AI")
            return Outcome(domain, "skipped", "already has AI", det.vendor)

        adapter = self._adapters.get(det.vendor)
        if adapter is None:
            self._ledger.advance(domain, "Dead", note=f"no adapter for {det.vendor}")
            return Outcome(domain, "skipped", f"no adapter for {det.vendor}", det.vendor)

        if dry_run:
            return Outcome(domain, "dry_run", "qualified; not sent (dry run)", det.vendor)

        result = adapter.send(domain, pitch, reply_email)
        if result.sent:
            self._ledger.mark_pitched(domain, pitch_variant=pitch_variant)
            return Outcome(domain, "pitched", "sent", det.vendor)
        # leave the Brand at Queued so a later run can retry it
        return Outcome(domain, "send_failed", result.detail or "send failed", det.vendor)
