import pytest

from chat_outreach_engine.ledger import Ledger, UnknownBrand, UnknownStage


def make(tmp_path):
    return Ledger(tmp_path / "ledger.db")


def test_new_brand_starts_queued(tmp_path):
    led = make(tmp_path)
    led.add_brand("example.com", vendor="gorgias")
    assert led.get_stage("example.com") == "Queued"


def test_add_brand_is_idempotent(tmp_path):
    led = make(tmp_path)
    led.add_brand("example.com", vendor="gorgias")
    led.mark_pitched("example.com", pitch_variant="A")
    # re-adding must NOT reset a Brand that has moved past Queued
    led.add_brand("example.com", vendor="gorgias")
    assert led.get_stage("example.com") == "Pitched"
    assert led.history("example.com") == [
        (s, t) for (s, t) in led.history("example.com")
    ]  # stable
    assert [s for s, _ in led.history("example.com")] == ["Queued", "Pitched"]


def test_a_brand_is_never_pitched_twice(tmp_path):
    led = make(tmp_path)
    led.add_brand("example.com", vendor="gorgias")
    assert led.mark_pitched("example.com", pitch_variant="A") is True
    assert led.can_pitch("example.com") is False
    # second attempt is refused and changes nothing
    assert led.mark_pitched("example.com", pitch_variant="B") is False
    assert led.get_stage("example.com") == "Pitched"
    assert led.get_pitch_variant("example.com") == "A"


def test_advance_records_append_only_history(tmp_path):
    led = make(tmp_path)
    led.add_brand("example.com", vendor="gorgias")
    led.advance("example.com", "Pitched", pitch_variant="A")
    led.advance("example.com", "Replied")
    led.advance("example.com", "Call Booked")
    stages = [s for s, _ in led.history("example.com")]
    assert stages == ["Queued", "Pitched", "Replied", "Call Booked"]
    assert led.get_stage("example.com") == "Call Booked"


def test_list_by_stage_and_vendor(tmp_path):
    led = make(tmp_path)
    led.add_brand("a.com", vendor="gorgias")
    led.add_brand("b.com", vendor="tidio")
    led.add_brand("c.com", vendor="gorgias")
    led.mark_pitched("a.com", pitch_variant="A")
    assert led.list_by_stage("Queued") == ["b.com", "c.com"]
    assert led.list_by_stage("Pitched") == ["a.com"]
    assert led.list_by_vendor("gorgias") == ["a.com", "c.com"]


def test_unknown_brand_raises(tmp_path):
    led = make(tmp_path)
    with pytest.raises(UnknownBrand):
        led.get_stage("nope.com")


def test_advance_to_unknown_stage_raises(tmp_path):
    led = make(tmp_path)
    led.add_brand("example.com", vendor="gorgias")
    with pytest.raises(UnknownStage):
        led.advance("example.com", "Banana")


def test_state_persists_across_reopen(tmp_path):
    db = tmp_path / "ledger.db"
    led = Ledger(db)
    led.add_brand("example.com", vendor="gorgias")
    led.mark_pitched("example.com", pitch_variant="A")
    led.close()
    reopened = Ledger(db)
    assert reopened.get_stage("example.com") == "Pitched"
    assert reopened.can_pitch("example.com") is False
