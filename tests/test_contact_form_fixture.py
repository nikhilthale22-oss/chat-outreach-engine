"""Proof that the offline contact-form path is GENERIC, not vendor-specific: the SAME test assertions
and the SAME shipped helpers (`_is_contact_form`, `_fill_role`, `_form_submit_locator`,
`_offline_form_message_field`) run against TWO very different real captured offline forms, differing
only by VendorConfig:

  - Olark  : page-DOM widget, widget_scope="#olark-container", fields id'd olark-custom-element-#N,
             a decoy page newsletter input outside the widget (scoping must avoid it). Captured live
             off bfyne.com 2026-07-19.
  - Tawk   : iframe widget, widget_scope=None, name="name"/name="email" inputs with aria-placeholder,
             an aria-label="Submit" button, all tawk-* classes. Captured live off
             leatherglovesonline.com 2026-07-19.

If both pass with only the config swapped, the contact-form build has no vendor-specific code. Skips
where Playwright/Chromium is unavailable so the pure-Python suite stays green everywhere.
"""
import pathlib

import pytest

from chat_outreach_engine.adapters.olark import OLARK
from chat_outreach_engine.adapters.tawk import TAWK
from chat_outreach_engine.widget_driver import WidgetDriver

pytest.importorskip("playwright.sync_api")

FIXDIR = pathlib.Path(__file__).parent / "fixtures"

# A render-normaliser applied identically to BOTH fixtures: un-hide each form control and its ancestor
# chain (real widgets show them via their own CSS, which set_content does not load) and shrink icons.
# It changes NO identifying attribute the helpers key on - it only makes the real DOM laid out.
NORMALIZE = """() => {
  const show = el => { while (el && el !== document.body) {
    const s = getComputedStyle(el);
    if (s.display === 'none') el.style.setProperty('display','block','important');
    el.style.setProperty('visibility','visible','important');
    el.style.setProperty('opacity','1','important');
    el.style.setProperty('position','static','important');
    el = el.parentElement; } };
  document.querySelectorAll('input,textarea,button').forEach(show);
  document.querySelectorAll('svg,img').forEach(e => { e.style.maxWidth='14px'; e.style.maxHeight='14px'; });
}"""

CASES = [
    {"label": "olark-pageDOM-scoped", "cfg": OLARK, "fixture": "olark_offline.html",
     "name_sel": "#olark-container input[placeholder*='name' i]",
     "email_sel": "#olark-container input[placeholder*='email' i]",
     "submit_has": "SEND", "submit_not": "SUBSCRIBE",
     "decoy": "input[name='contact[email]']"},         # page newsletter the scoping must skip
    {"label": "tawk-iframe-noscope", "cfg": TAWK, "fixture": "tawk_offline.html",
     "name_sel": "input[name='name']", "email_sel": "input[name='email']",
     "submit_has": "SUBMIT", "submit_not": None,
     "decoy": None},                                    # iframe surface is isolated; no page decoy
]


@pytest.fixture(params=CASES, ids=[c["label"] for c in CASES])
def case(request):
    from playwright.sync_api import sync_playwright
    c = request.param
    html = (FIXDIR / c["fixture"]).read_text()
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as e:
            pytest.skip(f"chromium unavailable: {e}")
        pg = browser.new_context().new_page()
        pg.set_content(html)
        pg.evaluate(NORMALIZE)
        try:
            yield c, pg
        finally:
            browser.close()


def test_recognized_as_a_contact_form(case):
    c, pg = case
    assert WidgetDriver(c["cfg"])._is_contact_form(pg) is True


def test_fills_the_widget_name_and_email(case):
    c, pg = case
    drv = WidgetDriver(c["cfg"])
    drv._fill_role(pg, "name", "Nikhil")
    drv._fill_role(pg, "email", "nikhilmercwise@zohomail.in")
    assert pg.locator(c["name_sel"]).first.input_value() == "Nikhil"
    assert pg.locator(c["email_sel"]).first.input_value() == "nikhilmercwise@zohomail.in"


def test_submit_locator_picks_the_widget_send(case):
    c, pg = case
    loc = WidgetDriver(c["cfg"])._form_submit_locator(pg)
    assert loc is not None
    label = loc.evaluate(
        "e => ((e.innerText||e.value||'') + ' ' + (e.getAttribute('aria-label')||'')).toUpperCase()")
    assert c["submit_has"] in label
    if c["submit_not"]:
        assert c["submit_not"] not in label


def test_message_field_is_found(case):
    c, pg = case
    assert WidgetDriver(c["cfg"])._offline_form_message_field(pg) is not None


def test_scoping_avoids_the_host_page_field(case):
    c, pg = case
    if not c["decoy"]:
        pytest.skip("iframe surface is isolated - no host-page field to collide with")
    drv = WidgetDriver(c["cfg"])
    drv._fill_role(pg, "email", "nikhilmercwise@zohomail.in")
    assert pg.locator(c["decoy"]).first.input_value() == ""
