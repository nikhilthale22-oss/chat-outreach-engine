"""Gate liveness: a Tidio store passes the gate only if its loader (code.tidio.co/<key>.js) is
actually being served. A stale static tag left behind by an expired/removed account (403/404)
must be filtered cheaply over HTTP - but a transient network blip must NOT false-kill a live
store (UNKNOWN stays retryable, not Dead). Fetches are injected so nothing hits the network.
"""
from chat_outreach_engine.batch import (
    LOADER_DEAD,
    LOADER_LIVE,
    LOADER_UNKNOWN,
    LiveAssessor,
    _tawk_loader_url,
    _tidio_loader_url,
    loader_liveness,
)

TAG = '<script src="//code.tidio.co/abc123.js" async></script>'
TAWK_TAG = '<script src="https://embed.tawk.to/5a4e68f94b401e45400bdeaa/default"></script>'


def test_loader_url_from_protocol_relative_tag():
    assert _tidio_loader_url(TAG) == "https://code.tidio.co/abc123.js"


def test_loader_url_from_https_tag():
    assert _tidio_loader_url("x https://code.tidio.co/Xy9z.js y") == "https://code.tidio.co/Xy9z.js"


def test_loader_url_absent_returns_none():
    assert _tidio_loader_url("<html>no tidio here</html>") is None
    assert _tidio_loader_url("") is None


def test_liveness_200_is_live():
    assert loader_liveness("u", fetch=lambda u: 200) == LOADER_LIVE


def test_liveness_403_and_404_are_dead():
    assert loader_liveness("u", fetch=lambda u: 403) == LOADER_DEAD
    assert loader_liveness("u", fetch=lambda u: 404) == LOADER_DEAD


def test_liveness_timeout_or_5xx_is_unknown_not_dead():
    def boom(u):
        raise TimeoutError()
    assert loader_liveness("u", fetch=boom) == LOADER_UNKNOWN
    assert loader_liveness("u", fetch=lambda u: 503) == LOADER_UNKNOWN


def test_liveness_no_url_is_unknown():
    assert loader_liveness(None, fetch=lambda u: 200) == LOADER_UNKNOWN


def _assessor(loader_status):
    return LiveAssessor(fetch=lambda d: TAG, loader_fetch=lambda u: loader_status)


def test_assessor_dead_loader_fails_gate_with_distinct_reason():
    a = _assessor(403)("store.com")
    assert a.vendor == "tidio" and a.gate_passed is False and a.gate_reason == "tidio loader dead"


def test_assessor_live_loader_passes_gate():
    assert _assessor(200)("store.com").gate_passed is True


def test_assessor_unknown_loader_is_retryable_not_dead():
    a = _assessor(503)("store.com")
    assert a.gate_passed is False and a.gate_reason == "loader unknown"


# The same dead-account-lingering-tag gate applies to Tawk (embed.tawk.to/<pid>/<wid>).

def test_tawk_loader_url_from_tag():
    assert _tawk_loader_url(TAWK_TAG) == "https://embed.tawk.to/5a4e68f94b401e45400bdeaa/default"


def test_tawk_loader_url_custom_widget_id():
    assert (_tawk_loader_url("x https://embed.tawk.to/686538b3e9265e190f81c03f/1iv5mb06s y")
            == "https://embed.tawk.to/686538b3e9265e190f81c03f/1iv5mb06s")


def test_tawk_loader_url_absent_returns_none():
    assert _tawk_loader_url("<html>no tawk here</html>") is None
    assert _tawk_loader_url("") is None


def _tawk_assessor(loader_status):
    return LiveAssessor(fetch=lambda d: TAWK_TAG, loader_fetch=lambda u: loader_status)


def test_assessor_dead_tawk_loader_fails_gate_with_distinct_reason():
    a = _tawk_assessor(404)("store.com")
    assert a.vendor == "tawk.to" and a.gate_passed is False and a.gate_reason == "tawk.to loader dead"


def test_assessor_live_tawk_loader_passes_gate():
    a = _tawk_assessor(200)("store.com")
    assert a.vendor == "tawk.to" and a.gate_passed is True


def test_assessor_unknown_tawk_loader_is_retryable():
    a = _tawk_assessor(502)("store.com")
    assert a.gate_passed is False and a.gate_reason == "loader unknown"
