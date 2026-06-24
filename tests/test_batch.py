"""BatchRunner tests.

The Assessor (live HTTP) and the Adapters (real browsers) are seams, so we fake them.
The Ledger is our own module, used real against a temp DB. We assert behaviour through the
public interface: the returned BatchReport and the Ledger state.
"""
from chat_outreach_engine.batch import Assessment, BatchRunner
from chat_outreach_engine.injector import SendResult
from chat_outreach_engine.ledger import Ledger

PITCHES = {"A": "PITCH-A", "B": "PITCH-B"}


class FakeAssessor:
    def __init__(self, table: dict):
        self.table = table
        self.calls: list[str] = []

    def __call__(self, domain: str) -> Assessment:
        self.calls.append(domain)
        return self.table[domain]


class FakeAdapter:
    def __init__(self, sent: bool = True, detail: str | None = None):
        self._sent = sent
        self._detail = detail if detail is not None else ("ok" if sent else "boom")
        self.calls: list[tuple] = []

    def send(self, domain, pitch, reply_email):
        self.calls.append((domain, pitch))
        return SendResult(self._sent, self._detail)


def assess(domain, fetched=True, has_widget=True, vendor="tidio", has_ai=False, gate=True):
    return Assessment(domain, fetched, has_widget, vendor, has_ai, gate)


def make(tmp_path, table, sent=True):
    led = Ledger(tmp_path / "l.db")
    adapter = FakeAdapter(sent=sent)
    runner = BatchRunner(led, {"tidio": adapter}, "me@x.com",
                         assessor=FakeAssessor(table), pitches=PITCHES, concurrency=2)
    return led, adapter, runner


def test_qualified_brand_is_pitched_with_variant_recorded(tmp_path):
    led, adapter, runner = make(tmp_path, {"ex.com": assess("ex.com")})
    report = runner.run(["ex.com"])
    assert report.counts.get("pitched") == 1
    assert led.get_stage("ex.com") == "Pitched"
    assert led.get_pitch_variant("ex.com") == "A"
    assert adapter.calls == [("ex.com", "PITCH-A")]


def test_brand_with_ai_is_dead_not_sent(tmp_path):
    led, adapter, runner = make(tmp_path, {"ex.com": assess("ex.com", has_ai=True)})
    report = runner.run(["ex.com"])
    assert report.counts.get("dead") == 1
    assert led.get_stage("ex.com") == "Dead"
    assert adapter.calls == []


def test_no_widget_is_dead(tmp_path):
    led, adapter, runner = make(tmp_path, {"ex.com": assess("ex.com", has_widget=False, vendor=None)})
    runner.run(["ex.com"])
    assert led.get_stage("ex.com") == "Dead"
    assert adapter.calls == []


def test_live_gate_failure_is_dead_not_sent(tmp_path):
    led, adapter, runner = make(tmp_path, {"ex.com": assess("ex.com", gate=False)})
    report = runner.run(["ex.com"])
    assert report.counts.get("dead") == 1
    assert "re-verify" in report.outcomes[0].reason
    assert led.get_stage("ex.com") == "Dead"
    assert adapter.calls == []


def test_vendor_without_adapter_is_dead(tmp_path):
    led, adapter, runner = make(tmp_path, {"ex.com": assess("ex.com", vendor="crisp")})
    runner.run(["ex.com"])
    assert led.get_stage("ex.com") == "Dead"
    assert adapter.calls == []


def test_fetch_failure_leaves_brand_queued_for_retry(tmp_path):
    led, adapter, runner = make(tmp_path, {"ex.com": assess("ex.com", fetched=False, has_widget=False, vendor=None)})
    report = runner.run(["ex.com"])
    assert report.counts.get("fetch_failed") == 1
    assert led.get_stage("ex.com") == "Queued"
    assert led.can_pitch("ex.com") is True
    assert adapter.calls == []


def test_send_failure_leaves_brand_queued_for_retry(tmp_path):
    led, adapter, runner = make(tmp_path, {"ex.com": assess("ex.com")}, sent=False)
    report = runner.run(["ex.com"])
    assert report.counts.get("send_failed") == 1
    assert led.get_stage("ex.com") == "Queued"
    assert led.can_pitch("ex.com") is True


def test_dry_run_qualifies_but_sends_nothing(tmp_path):
    led, adapter, runner = make(tmp_path, {"ex.com": assess("ex.com")})
    report = runner.run(["ex.com"], dry_run=True)
    assert report.counts.get("would_pitch") == 1
    assert report.outcomes[0].variant == "A"
    assert led.get_stage("ex.com") == "Queued"
    assert adapter.calls == []


def test_variants_alternate_across_qualified_brands(tmp_path):
    table = {f"d{i}.com": assess(f"d{i}.com") for i in range(4)}
    led, adapter, runner = make(tmp_path, table)
    runner.run(["d0.com", "d1.com", "d2.com", "d3.com"])
    assert [led.get_pitch_variant(f"d{i}.com") for i in range(4)] == ["A", "B", "A", "B"]
    # the adapter received the matching pitch for each variant
    sent = dict(adapter.calls)
    assert sent["d0.com"] == "PITCH-A" and sent["d1.com"] == "PITCH-B"


def test_rerun_is_resumable_and_does_not_reassess_or_repitch(tmp_path):
    table = {"ex.com": assess("ex.com")}
    led = Ledger(tmp_path / "l.db")
    adapter = FakeAdapter()
    fa = FakeAssessor(table)
    runner = BatchRunner(led, {"tidio": adapter}, "me@x.com", assessor=fa, pitches=PITCHES)
    runner.run(["ex.com"])
    runner.run(["ex.com"])
    assert adapter.calls == [("ex.com", "PITCH-A")]   # pitched once
    assert fa.calls == ["ex.com"]                      # assessed once (skipped on rerun)


def test_duplicate_input_domains_are_deduped(tmp_path):
    led, adapter, runner = make(tmp_path, {"ex.com": assess("ex.com")})
    report = runner.run(["ex.com", "EX.com", " ex.com "])
    assert len([o for o in report.outcomes if o.domain == "ex.com"]) == 1
    assert adapter.calls == [("ex.com", "PITCH-A")]


def test_terminal_send_failure_is_marked_dead_not_retried(tmp_path):
    led = Ledger(tmp_path / "l.db")
    adapter = FakeAdapter(sent=False, detail="prechat_blocked_required_fields")
    runner = BatchRunner(led, {"tidio": adapter}, "me@x.com",
                         assessor=FakeAssessor({"ex.com": assess("ex.com")}), pitches=PITCHES)
    report = runner.run(["ex.com"])
    assert report.counts.get("dead") == 1
    assert led.get_stage("ex.com") == "Dead"   # never retried again


def test_transient_send_failures_are_capped_and_then_dead(tmp_path):
    led = Ledger(tmp_path / "l.db")
    adapter = FakeAdapter(sent=False, detail="no_tidio_api")
    table = {"ex.com": assess("ex.com")}
    runner = BatchRunner(led, {"tidio": adapter}, "me@x.com",
                         assessor=FakeAssessor(table), pitches=PITCHES, max_attempts=2)
    runner.run(["ex.com"])
    assert led.get_stage("ex.com") == "Queued"  # 1st failure: still retryable
    report = runner.run(["ex.com"])
    assert led.get_stage("ex.com") == "Dead"    # 2nd failure hits the cap -> Dead
    assert report.counts.get("dead") == 1


def test_limit_applies_to_fresh_work_not_already_done_brands(tmp_path):
    led = Ledger(tmp_path / "l.db")
    led.add_brand("done.com")
    led.advance("done.com", "Dead", note="prior run")
    adapter = FakeAdapter()
    table = {"done.com": assess("done.com"), "fresh.com": assess("fresh.com")}
    runner = BatchRunner(led, {"tidio": adapter}, "me@x.com",
                         assessor=FakeAssessor(table), pitches=PITCHES)
    report = runner.run(["done.com", "fresh.com"], dry_run=True, limit=1)
    # limit=1 should spend its budget on the fresh brand, not be consumed by the done one
    assert any(o.domain == "fresh.com" and o.action == "would_pitch" for o in report.outcomes)
