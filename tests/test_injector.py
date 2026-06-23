"""Injector orchestration tests.

The Detector and Adapter are seams (real ones hit the network / a browser), so we
fake them. The Ledger is our own module, so we use the real one against a temp DB.
"""
from chat_outreach_engine.injector import Detection, Injector, SendResult
from chat_outreach_engine.ledger import Ledger


class FakeDetector:
    def __init__(self, detection: Detection):
        self._detection = detection

    def detect(self, domain: str) -> Detection:
        return self._detection


class FakeAdapter:
    def __init__(self, sent: bool = True):
        self._sent = sent
        self.calls: list[str] = []

    def send(self, domain: str, pitch: str, reply_email: str) -> SendResult:
        self.calls.append(domain)
        return SendResult(self._sent, "ok" if self._sent else "boom")


def ledger(tmp_path):
    return Ledger(tmp_path / "ledger.db")


def make(tmp_path, detection, sent=True):
    led = ledger(tmp_path)
    adapter = FakeAdapter(sent=sent)
    inj = Injector(led, FakeDetector(detection), {"gorgias": adapter})
    return led, adapter, inj


def test_qualified_gorgias_brand_is_pitched_and_recorded(tmp_path):
    led, adapter, inj = make(tmp_path, Detection(True, "gorgias", False))
    out = inj.process("ex.com", "hi", "me@x.com", pitch_variant="A")
    assert out.action == "pitched"
    assert led.get_stage("ex.com") == "Pitched"
    assert led.get_pitch_variant("ex.com") == "A"
    assert adapter.calls == ["ex.com"]


def test_brand_with_ai_is_skipped_not_sent(tmp_path):
    led, adapter, inj = make(tmp_path, Detection(True, "intercom", True))
    out = inj.process("ex.com", "hi", "me@x.com")
    assert out.action == "skipped" and "AI" in out.reason
    assert led.get_stage("ex.com") == "Dead"
    assert adapter.calls == []


def test_brand_with_no_widget_is_skipped_gracefully(tmp_path):
    led, adapter, inj = make(tmp_path, Detection(False, None, False))
    out = inj.process("ex.com", "hi", "me@x.com")
    assert out.action == "skipped" and "widget" in out.reason
    assert led.get_stage("ex.com") == "Dead"
    assert adapter.calls == []


def test_vendor_with_no_adapter_is_recorded(tmp_path):
    led, adapter, inj = make(tmp_path, Detection(True, "tidio", False))
    out = inj.process("ex.com", "hi", "me@x.com")
    assert out.action == "skipped" and "adapter" in out.reason
    assert led.get_stage("ex.com") == "Dead"
    assert adapter.calls == []


def test_dry_run_qualifies_but_does_not_send_or_change_stage(tmp_path):
    led, adapter, inj = make(tmp_path, Detection(True, "gorgias", False))
    out = inj.process("ex.com", "hi", "me@x.com", dry_run=True)
    assert out.action == "dry_run"
    assert led.get_stage("ex.com") == "Queued"
    assert adapter.calls == []


def test_send_failure_leaves_brand_queued_for_retry(tmp_path):
    led, adapter, inj = make(tmp_path, Detection(True, "gorgias", False), sent=False)
    out = inj.process("ex.com", "hi", "me@x.com")
    assert out.action == "send_failed"
    assert led.get_stage("ex.com") == "Queued"
    assert led.can_pitch("ex.com") is True


def test_already_pitched_brand_is_not_repitched(tmp_path):
    led, adapter, inj = make(tmp_path, Detection(True, "gorgias", False))
    inj.process("ex.com", "hi", "me@x.com")
    out = inj.process("ex.com", "hi", "me@x.com")
    assert out.action == "skipped" and "already" in out.reason
    assert adapter.calls == ["ex.com"]  # not called a second time
