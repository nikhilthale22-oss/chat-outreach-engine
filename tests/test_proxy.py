"""Proxy config tests: env -> Playwright dict / requests URL, with credential encoding."""
import os

from chat_outreach_engine.proxy import playwright_proxy, requests_proxies


def _clear(monkeypatch):
    for k in ("PROXY_SERVER", "PROXY_USERNAME", "PROXY_PASSWORD"):
        monkeypatch.delenv(k, raising=False)


def test_unset_proxy_is_none(monkeypatch):
    _clear(monkeypatch)
    assert playwright_proxy() is None
    assert requests_proxies() is None


def test_playwright_proxy_keeps_credentials_separate(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("PROXY_SERVER", "http://host:8000")
    monkeypatch.setenv("PROXY_USERNAME", "u")
    monkeypatch.setenv("PROXY_PASSWORD", "p@ss/word")
    assert playwright_proxy() == {"server": "http://host:8000", "username": "u",
                                  "password": "p@ss/word"}


def test_requests_proxies_percent_encodes_credentials(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("PROXY_SERVER", "http://host:8000")
    monkeypatch.setenv("PROXY_USERNAME", "user")
    monkeypatch.setenv("PROXY_PASSWORD", "p@ss/w#rd")
    url = requests_proxies()["https"]
    # special chars are encoded so the URL stays parseable
    assert url == "http://user:p%40ss%2Fw%23rd@host:8000"
