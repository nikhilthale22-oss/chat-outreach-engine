"""Pure-helper tests for the Tidio adapter (the send() flow itself needs a live browser and is
exercised by real runs). _target_url is the seam that lets us point the adapter at an explicit
URL - a bare domain gets https, an explicit scheme is preserved (http test pages, http-only stores).
"""
from chat_outreach_engine.adapters.tidio import TidioAdapter


def test_target_url_prefixes_bare_domain_with_https():
    assert TidioAdapter._target_url("foo.com") == "https://foo.com"


def test_target_url_preserves_explicit_http_scheme():
    assert TidioAdapter._target_url("http://localhost:8088/") == "http://localhost:8088/"


def test_target_url_preserves_explicit_https_scheme():
    assert TidioAdapter._target_url("https://shop.example.com/page") == "https://shop.example.com/page"
