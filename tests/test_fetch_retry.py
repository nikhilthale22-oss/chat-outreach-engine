"""Reach-robustness for the FREE (no-proxy) path: a single datacenter IP gets HTTP 429'd in
bursts, so the assessor fetch must back off and retry rate-limits instead of returning the 429
error page (which matched no widget and falsely marked the Brand Dead - burning reachable stores).
The retry policy is injectable (get/sleep) so it is tested without real HTTP.
"""
from chat_outreach_engine.batch import (
    _backoff_seconds,
    _is_retryable_status,
    fetch_html,
)


def test_retryable_statuses_are_429_and_5xx_only():
    assert _is_retryable_status(429)
    assert _is_retryable_status(500)
    assert _is_retryable_status(503)
    assert not _is_retryable_status(200)
    assert not _is_retryable_status(403)
    assert not _is_retryable_status(404)


def test_backoff_grows_exponentially_then_caps():
    assert _backoff_seconds(0) == 0.5
    assert _backoff_seconds(1) == 1.0
    assert _backoff_seconds(2) == 2.0
    assert _backoff_seconds(20) == 8.0          # capped


def test_2xx_returns_body_with_no_retry():
    calls, slept = [], []
    def get(url):
        calls.append(url)
        return 200, "<html>store</html>"
    html = fetch_html("ex.com", get=get, sleep=slept.append)
    assert html == "<html>store</html>"
    assert calls == ["https://ex.com"] and slept == []


def test_429_then_200_recovers_after_one_backoff():
    seq = [(429, "rate limited"), (200, "<html>store</html>")]
    calls, slept = [], []
    def get(url):
        calls.append(url)
        return seq[len(calls) - 1]
    html = fetch_html("ex.com", get=get, sleep=slept.append)
    assert html == "<html>store</html>"
    assert slept == [0.5]                        # backed off once, then succeeded


def test_persistent_429_returns_empty_so_brand_stays_queued_not_dead():
    # The key fix: a rate-limited store must NOT come back as the 429 page (which reads as
    # "no widget" -> Dead). Empty result => batch leaves it Queued (retryable).
    slept = []
    html = fetch_html("ex.com", get=lambda url: (429, "429 page"),
                      sleep=slept.append, attempts=3)
    assert html == ""
    assert slept == [0.5, 1.0, 0.5, 1.0]         # 3 attempts x 2 schemes, no sleep on the last of each


def test_403_is_not_retried_here_and_yields_empty():
    calls, slept = [], []
    def get(url):
        calls.append(url)
        return 403, "forbidden"
    html = fetch_html("ex.com", get=get, sleep=slept.append)
    assert html == "" and slept == []
    assert calls == ["https://ex.com", "http://ex.com"]   # each scheme tried once, no backoff


def test_https_connection_error_falls_back_to_http():
    def get(url):
        if url.startswith("https://"):
            raise ConnectionError("tls boom")
        return 200, "<html>http store</html>"
    html = fetch_html("ex.com", get=get, sleep=lambda s: None)
    assert html == "<html>http store</html>"
