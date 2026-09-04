"""Phase 2 route tests: vendor -> send-or-skip decisions, with gated = skip."""
from chat_outreach_engine.injector import Detection
from chat_outreach_engine.route import registry
from chat_outreach_engine.route.router import route


def _det(vendor, kind="human", has_widget=True):
    return Detection(has_widget=has_widget, vendor=vendor, has_ai=(kind == "ai"),
                     kind=kind, category=None)


def test_human_vendor_routes_to_headed():
    r = route(_det("tawk.to"))
    assert r.action == "send" and r.method == registry.METHOD_HEADED


def test_crisp_routes_to_headed():
    assert route(_det("crisp")).method == "headed"


def test_dropped_api_vendors_are_skipped():
    # ADR-0008: API send dropped (0 vendors proven end to end). Gorgias/Intercom are no longer
    # routed - with no card they fall through to no_method (skip), like any unsupported vendor.
    for vendor in ("gorgias", "intercom"):
        r = route(_det(vendor))
        assert r.action == "skip" and r.reason == "no_method"


def test_shopify_inbox_is_skipped_gated():
    r = route(_det("shopify-inbox", kind="hybrid"))
    assert r.action == "skip" and r.reason == "gated"


def test_shopify_agent_is_skipped_gated():
    assert route(_det("shopify-agent", kind="ai")).reason == "gated"


def test_no_widget_is_skipped():
    r = route(_det(None, has_widget=False))
    assert r.action == "skip" and r.reason == "no_widget"


def test_unknown_vendor_has_no_method():
    r = route(_det("some-brand-new-vendor"))
    assert r.action == "skip" and r.reason == "no_method"
