"""SignatureDetector: the real Detector, reusing the absorbed signatures library.

Fetches a Brand's homepage and matches the 62-vendor signature set to find the
Chat Widget vendor and whether it is an AI vendor. Network access is lazy so the
module imports cleanly in test environments that fake the Detector.
"""
from __future__ import annotations

from . import signatures
from .injector import Detection

# Vendors in this category already have AI behind the chat, so they are not Qualified.
AI_CATEGORY = "ai-chat"

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")


class SignatureDetector:
    def __init__(self) -> None:
        signatures.compile_patterns()

    def detect(self, domain: str) -> Detection:
        html = self._fetch(domain)
        hits = signatures.match_html(html) if html else []
        if not hits:
            return Detection(has_widget=False, vendor=None, has_ai=False)
        vendor = hits[0]["vendor"]
        has_ai = any(h.get("category") == AI_CATEGORY for h in hits)
        return Detection(has_widget=True, vendor=vendor, has_ai=has_ai)

    @staticmethod
    def _fetch(domain: str) -> str:
        import requests
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        headers = {"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"}
        for scheme in ("https://", "http://"):
            try:
                r = requests.get(scheme + domain, headers=headers, timeout=15,
                                 verify=False, allow_redirects=True)
                return (r.text or "")[:2_000_000]
            except Exception:
                continue
        return ""
