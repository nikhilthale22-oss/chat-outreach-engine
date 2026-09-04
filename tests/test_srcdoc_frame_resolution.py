"""Regression: Tawk's v4 panel is an about:srcdoc iframe that HEADLESS Chromium does not attach to
page.frames, so a marker lookup over page.frames alone found nothing headless and every Tawk store
fell to no_composer (the 0/11 regression). _candidate_frames must ALSO resolve <iframe> elements via
content_frame(), which returns the srcdoc frame headless. These fakes prove both sources are consulted
without a browser; the end-to-end proof is a live dry_run on the box (composer_reached)."""
from chat_outreach_engine.adapters.tawk import TAWK
from chat_outreach_engine.adapters.chatra import CHATRA
from chat_outreach_engine.widget_driver import WidgetDriver


class _Loc:
    def __init__(self, n):
        self._n = n

    def count(self):
        return self._n


class _Frame:
    def __init__(self, url="", markers=0):
        self.url = url
        self._m = markers

    def locator(self, sel):
        return _Loc(self._m)


class _El:
    def __init__(self, frame):
        self._f = frame

    def content_frame(self):
        return self._f


class _Page:
    def __init__(self, frames, iframe_els):
        self._frames = frames
        self._els = iframe_els
        self.main_frame = frames[0]

    @property
    def frames(self):
        return self._frames

    def query_selector_all(self, sel):
        return self._els


def test_marker_frame_found_only_via_content_frame_when_page_frames_omits_it():
    # page.frames = main + a real-URL frame with NO marker (what headless reports for Tawk); the panel
    # is reachable ONLY through the <iframe> element's content_frame().
    main = _Frame(url="https://store.example")
    google = _Frame(url="https://www.google.com/recaptcha", markers=0)
    panel = _Frame(url="about:srcdoc", markers=1)
    page = _Page(frames=[main, google], iframe_els=[_El(google), _El(panel)])
    d = WidgetDriver(TAWK)
    cands = d._candidate_frames(page, marker=".tawk-chat-panel", url_sub=None)
    assert panel in cands and google not in cands and main not in cands


def test_url_substring_frame_is_matched_from_page_frames():
    # LiveChat/Chatra resolve by URL substring; a page.frames frame whose url carries it qualifies.
    main = _Frame(url="https://store.example")
    widget = _Frame(url="https://chat.chatra.io/widget")
    page = _Page(frames=[main, widget], iframe_els=[])
    d = WidgetDriver(CHATRA)
    cands = d._candidate_frames(page, marker=None, url_sub="chatra.io")
    assert cands == [widget]


def test_no_duplicate_when_a_frame_is_seen_in_both_sources():
    main = _Frame(url="https://store.example")
    widget = _Frame(url="https://chat.chatra.io/widget")
    page = _Page(frames=[main, widget], iframe_els=[_El(widget)])   # same frame object both ways
    d = WidgetDriver(CHATRA)
    cands = d._candidate_frames(page, marker=None, url_sub="chatra.io")
    assert cands == [widget]        # deduped, not [widget, widget]
