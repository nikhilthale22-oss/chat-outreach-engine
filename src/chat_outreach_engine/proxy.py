"""Residential-proxy config, read from the environment, used by both the browser Adapters
(Playwright) and the live assessment fetch (requests).

Server #1's datacenter IP gets blocked by anti-bot on many brand sites, so at volume we route
through a residential proxy (ProxyBase). Set these env vars to enable it; unset = direct (fine
for the Mac, which already has a residential IP):

    PROXY_SERVER=http://host:port        (or socks5://host:port)
    PROXY_USERNAME=...                    (optional)
    PROXY_PASSWORD=...                    (optional)
"""
from __future__ import annotations

import os
from urllib.parse import quote


def playwright_proxy() -> dict | None:
    """A proxy dict for Playwright new_context(proxy=...), or None when unset."""
    server = os.environ.get("PROXY_SERVER")
    if not server:
        return None
    proxy: dict = {"server": server}
    user = os.environ.get("PROXY_USERNAME")
    password = os.environ.get("PROXY_PASSWORD")
    if user:
        proxy["username"] = user
    if password:
        proxy["password"] = password
    return proxy


def requests_proxies() -> dict | None:
    """A proxies dict for requests.get(proxies=...), or None when unset. Credentials are
    folded into the URL (requests has no separate auth arg for proxies)."""
    server = os.environ.get("PROXY_SERVER")
    if not server:
        return None
    user = os.environ.get("PROXY_USERNAME")
    password = os.environ.get("PROXY_PASSWORD")
    if user and password and "://" in server:
        scheme, host = server.split("://", 1)
        # Percent-encode credentials so special chars (@ : / # ...) don't corrupt the URL.
        url = f"{scheme}://{quote(user, safe='')}:{quote(password, safe='')}@{host}"
    else:
        url = server
    return {"http": url, "https": url}
