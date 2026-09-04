"""Pipeline (Phase 3 spine) tests: detect -> route -> send, composed.

The detector and adapters are faked so the unit is exercised with no network and no browser:
we assert the right fork is taken (skip vs send), that a send hits the correct adapter with the
right args, and that dry_run never sends.
"""
from chat_outreach_engine.injector import Detection, SendResult
from chat_outreach_engine.pipeline import Pipeline


class FakeDetector:
    def __init__(self, detection: Detection):
        self._detection = detection
        self.seen = []

    def detect(self, domain: str) -> Detection:
        self.seen.append(domain)
        return self._detection


class RecordingAdapter:
    def __init__(self, result: SendResult):
        self._result = result
        self.calls = []

    def send(self, domain, pitch, reply_email) -> SendResult:
        self.calls.append((domain, pitch, reply_email))
        return self._result


def _detection(vendor, kind="human", has_widget=True, has_ai=False):
    return Detection(has_widget=has_widget, vendor=vendor, has_ai=has_ai,
                     kind=kind, category=None)


def _pipeline(detection, adapters):
    return Pipeline(detector=FakeDetector(detection), adapters=adapters,
                    reply_email="reply@example.com")


def test_no_widget_is_skipped_and_never_sends():
    adapter = RecordingAdapter(SendResult(True, "delivered"))
    p = _pipeline(_detection(None, has_widget=False), {"tawk.to": adapter})
    r = p.run_one("nowidget.com", "hi")
    assert r.action == "skipped" and r.reason == "no_widget"
    assert adapter.calls == []


def test_gated_vendor_is_skipped_and_never_sends():
    adapter = RecordingAdapter(SendResult(True, "delivered"))
    p = _pipeline(_detection("shopify-inbox", kind="hybrid"), {"tawk.to": adapter})
    r = p.run_one("gatedstore.com", "hi")
    assert r.action == "skipped" and r.reason == "gated"
    assert adapter.calls == []


def test_unsupported_vendor_is_skipped_no_method():
    adapter = RecordingAdapter(SendResult(True, "delivered"))
    p = _pipeline(_detection("some-new-vendor"), {"tawk.to": adapter})
    r = p.run_one("unknown.com", "hi")
    assert r.action == "skipped" and r.reason == "no_method"
    assert adapter.calls == []


def test_headed_vendor_sends_via_its_adapter():
    adapter = RecordingAdapter(SendResult(True, "delivered"))
    p = _pipeline(_detection("tawk.to"), {"tawk.to": adapter})
    r = p.run_one("EmeraldFineJewelry.com", "the pitch")
    assert r.action == "sent" and r.vendor == "tawk.to" and r.method == "headed"
    assert r.detail == "delivered"
    # domain normalized to lower-case; pitch + reply email threaded through to the adapter
    assert adapter.calls == [("emeraldfinejewelry.com", "the pitch", "reply@example.com")]


def test_headed_vendor_send_failure_reports_failed_with_detail():
    adapter = RecordingAdapter(SendResult(False, "no_composer"))
    p = _pipeline(_detection("tawk.to"), {"tawk.to": adapter})
    r = p.run_one("stalestore.com", "the pitch")
    assert r.action == "failed" and r.detail == "no_composer"
    assert adapter.calls  # a send WAS attempted (failure is a real send result, not a skip)


def test_headed_vendor_missing_adapter_is_skipped():
    p = _pipeline(_detection("crisp"), {})   # routed headed, but no card in the map
    r = p.run_one("crispstore.com", "hi")
    assert r.action == "skipped" and r.reason == "no_adapter" and r.method == "headed"


def test_dry_run_reaches_would_send_without_sending():
    adapter = RecordingAdapter(SendResult(True, "delivered"))
    p = _pipeline(_detection("tawk.to"), {"tawk.to": adapter})
    r = p.run_one("emeraldfinejewelry.com", "the pitch", dry_run=True)
    assert r.action == "would_send" and r.vendor == "tawk.to" and r.method == "headed"
    assert adapter.calls == []
