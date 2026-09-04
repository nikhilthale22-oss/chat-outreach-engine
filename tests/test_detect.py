"""Phase 1 detect tests: vendor fingerprint precision + AI-vs-human classification.

Hermetic (no network): match_html and kind_for run on fixed HTML snippets, and
detect() is exercised with a patched _fetch.
"""
from chat_outreach_engine.detect import signatures
from chat_outreach_engine.detect.detector import SignatureDetector
from chat_outreach_engine.injector import Detection

signatures.compile_patterns()


# ---- vendor fingerprint precision (Layer 1) ----

def test_matches_tawk_by_script():
    hits = signatures.match_html('<script src="https://embed.tawk.to/64/abc"></script>')
    assert hits and hits[0]["vendor"] == "tawk.to"


def test_matches_shopify_inbox_by_messaging_api():
    hits = signatures.match_html('<script src="https://messaging-api.shopifyapps.com/x.js"></script>')
    assert any(h["vendor"] == "shopify-inbox" for h in hits)


def test_matches_shopify_agent_ai_by_custom_element():
    # Shopify's JS-injected AI assistant: static HTML has <shopify-agent>, not messaging-api
    hits = signatures.match_html('<shopify-agent theme="light"></shopify-agent>')
    assert hits and hits[0]["vendor"] == "shopify-agent"
    assert signatures.kind_for("shopify-agent", "ecommerce-chat") == "ai"


def test_matches_ada_by_script():
    hits = signatures.match_html('<script src="https://static.ada.support/embed2.js"></script>')
    assert hits and hits[0]["vendor"] == "ada"


def test_no_false_positive_on_bare_shopify():
    # a generic launcher class + navigator.sendBeacon must NOT trip any Layer-1 rule
    html = '<div class="launcher"></div><script>navigator.sendBeacon("/t")</script>'
    assert signatures.match_html(html) == []


# ---- AI vs human classification ----

def test_kind_human_for_live_chat_vendors():
    assert signatures.kind_for("tawk.to", "live-chat") == "human"
    assert signatures.kind_for("crisp", "live-chat") == "human"


def test_kind_ai_for_ai_native_and_commerce_ai():
    assert signatures.kind_for("ada", "ai-chat") == "ai"
    assert signatures.kind_for("zipchat", "ecommerce-chat") == "ai"


def test_kind_hybrid_for_shopify_inbox_and_intercom():
    # Shopify's chat now fronts the Storekick AI agent; Intercom commonly runs Fin
    assert signatures.kind_for("shopify-inbox", "ecommerce-chat") == "hybrid"
    assert signatures.kind_for("intercom", "live-chat") == "hybrid"


def test_kind_unknown_for_no_vendor():
    assert signatures.kind_for(None, None) == "unknown"


# ---- end-to-end detect() with a patched fetch (no network) ----

def test_detect_human_store(monkeypatch):
    monkeypatch.setattr(SignatureDetector, "_fetch",
                        staticmethod(lambda domain: '<script src="https://embed.tawk.to/6/a"></script>'))
    det = SignatureDetector().detect("brand.com")
    assert isinstance(det, Detection)
    assert det.has_widget and det.vendor == "tawk.to"
    assert det.kind == "human" and det.has_ai is False


def test_detect_ai_store(monkeypatch):
    monkeypatch.setattr(SignatureDetector, "_fetch",
                        staticmethod(lambda domain: '<script src="https://static.ada.support/e.js"></script>'))
    det = SignatureDetector().detect("brand.com")
    assert det.vendor == "ada" and det.kind == "ai" and det.has_ai is True


def test_detect_no_widget(monkeypatch):
    monkeypatch.setattr(SignatureDetector, "_fetch", staticmethod(lambda domain: "<html>plain</html>"))
    det = SignatureDetector().detect("brand.com")
    assert det.has_widget is False and det.vendor is None and det.kind == "unknown"
