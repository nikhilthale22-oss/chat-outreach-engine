#!/usr/bin/env python3
"""SPIKE: find + dump the Shopify native contact form structure (NO submit). For each store, try the
usual contact URLs, locate the form that carries an email field + a message textarea, and dump its
action/method/fields + any captcha. Tells us the exact fields to fill and how uniform they are before
building the ContactForm delivery path.

Usage: python3 research/contact_form_spike.py <list.txt> [N]
"""
import json, os, sys, time

CANDIDATE_PATHS = ["/pages/contact", "/pages/contact-us", "/contact", "/contact-us", "/pages/contact_us"]

FORM_JS = """
() => {
  const vis = (el) => { try { return el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}); } catch(e){ return !!(el.offsetWidth||el.offsetHeight); } };
  const forms = Array.from(document.querySelectorAll('form'));
  // pick the form that has an email-ish input AND a textarea (the contact form)
  let best = null;
  for (const f of forms) {
    const email = f.querySelector("input[type='email'], input[name*='email' i]");
    const ta = f.querySelector('textarea');
    if (email && ta && vis(f)) { best = f; break; }
  }
  if (!best) {
    // fall back: any form posting to /contact
    best = forms.find(f => (f.getAttribute('action')||'').includes('/contact')) || null;
  }
  if (!best) return {found:false, formCount:forms.length};
  const fields = [];
  for (const el of best.querySelectorAll('input, textarea, select')) {
    fields.push({tag: el.tagName.toLowerCase(), name: el.getAttribute('name')||'',
                 type: el.getAttribute('type')||'', ph: (el.getAttribute('placeholder')||el.getAttribute('aria-label')||'').slice(0,30),
                 required: el.required || el.getAttribute('aria-required')==='true'});
  }
  const html = best.outerHTML;
  const captcha = /hcaptcha|h-captcha/i.test(html) ? 'hcaptcha'
    : /g-recaptcha|recaptcha/i.test(html) ? 'recaptcha'
    : /turnstile/i.test(html) ? 'turnstile' : 'none';
  return {found:true, action: best.getAttribute('action')||'', method: (best.getAttribute('method')||'get').toLowerCase(),
          fields: fields.filter(f => f.type!=='hidden' || /contact|form_type/.test(f.name)), captcha};
}
"""


def probe(page, domain):
    for path in CANDIDATE_PATHS:
        url = "https://" + domain + path
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=25000)
            if resp and resp.status >= 400:
                continue
            time.sleep(1.5)
            r = page.evaluate(FORM_JS)
            if r.get("found"):
                r["url"] = path
                return r
        except Exception:
            continue
    return {"found": False, "note": "no contact form at usual paths"}


def run(domains, n):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        channel = os.environ.get("BROWSER_CHANNEL", "chrome") or None
        browser = p.chromium.launch(headless=True, channel=channel,
                                    args=["--disable-blink-features=AutomationControlled"])
        found = 0
        for d in domains[:n]:
            page = browser.new_context(viewport={"width": 1366, "height": 900}, locale="en-US",
                user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")).new_page()
            try:
                r = probe(page, d)
            except Exception as e:
                r = {"found": False, "error": f"{type(e).__name__}: {str(e)[:60]}"}
            if r.get("found"):
                found += 1
                names = [f["name"] for f in r.get("fields", []) if f["name"]]
                print(f"{d:38} {r['url']:18} action={r['action'][:20]} method={r['method']} "
                      f"captcha={r['captcha']} fields={names}")
            else:
                print(f"{d:38} NOT FOUND ({r.get('note') or r.get('error','')})")
            sys.stdout.flush()
            try:
                page.context.close()
            except Exception:
                pass
        print(f"\n== contact form found on {found}/{min(n,len(domains))} ==")
        browser.close()


if __name__ == "__main__":
    lst = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    if lst == "-arova":
        domains = ["arova-5265.myshopify.com"]
    else:
        domains = [x.strip() for x in open(lst) if x.strip()]
        import random
        random.seed(9); random.shuffle(domains)
        domains = ["arova-5265.myshopify.com"] + domains  # always include the mock store first
    run(domains, n)
