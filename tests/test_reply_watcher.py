"""ReplyWatcher tests. The inbox fetch is a seam (real one is IMAP), so we fake it with a
list of Emails. The Ledger is real against a temp DB.
"""
from chat_outreach_engine.ledger import Ledger
from chat_outreach_engine.reply_watcher import Email, ReplyWatcher, default_matcher


def pitched_ledger(tmp_path, domains):
    led = Ledger(tmp_path / "l.db")
    for d in domains:
        led.add_brand(d)
        led.mark_pitched(d, pitch_variant="A")
    return led


def watcher(led, emails):
    return ReplyWatcher(led, fetch_unseen=lambda: list(emails))


def test_reply_matching_a_pitched_brand_advances_it_to_replied(tmp_path):
    led = pitched_ledger(tmp_path, ["wristoutfitters.com"])
    w = watcher(led, [Email("support@wristoutfitters.com", "Re: your message", "sure, tell me more")])
    results = w.poll()
    assert led.get_stage("wristoutfitters.com") == "Replied"
    assert results == [(results[0][0], "wristoutfitters.com")]


def test_match_by_brand_token_in_body_when_domain_not_literal(tmp_path):
    led = pitched_ledger(tmp_path, ["nayaswimwear.com"])
    w = watcher(led, [Email("noreply@tidio.email", "New message from Naya Swimwear",
                            "A visitor reply from nayaswimwear")])
    w.poll()
    assert led.get_stage("nayaswimwear.com") == "Replied"


def test_unmatched_reply_changes_nothing(tmp_path):
    led = pitched_ledger(tmp_path, ["wristoutfitters.com"])
    w = watcher(led, [Email("newsletter@randomstore.com", "50% off sale", "shop now")])
    results = w.poll()
    assert led.get_stage("wristoutfitters.com") == "Pitched"
    assert results == [(results[0][0], None)]


def test_only_pitched_brands_are_matched_not_queued(tmp_path):
    led = Ledger(tmp_path / "l.db")
    led.add_brand("queuedstore.com")  # Queued, never pitched
    w = watcher(led, [Email("hi@queuedstore.com", "hello", "queuedstore.com replying")])
    w.poll()
    assert led.get_stage("queuedstore.com") == "Queued"


def test_reply_is_idempotent_across_polls(tmp_path):
    led = pitched_ledger(tmp_path, ["wristoutfitters.com"])
    emails = [Email("support@wristoutfitters.com", "Re:", "interested")]
    ReplyWatcher(led, fetch_unseen=lambda: list(emails)).poll()
    # a later poll re-delivering the same email must not error or re-advance
    second = ReplyWatcher(led, fetch_unseen=lambda: list(emails)).poll()
    assert led.get_stage("wristoutfitters.com") == "Replied"
    assert second == [(second[0][0], None)]  # already Replied -> not in Pitched set -> unmatched


def test_longest_domain_wins_on_overlap(tmp_path):
    led = pitched_ledger(tmp_path, ["foo.com", "shop.foo.com"])
    matched = default_matcher(Email("x@shop.foo.com", "", ""), {"foo.com", "shop.foo.com"})
    assert matched == "shop.foo.com"


# A real reply we received (support@glamnetic.com): an automated Gorgias CSAT, not a human.
# It must NOT advance the Brand to Replied or it is a false positive. Body is the verbatim text.
GLAMNETIC_CSAT = (
    "Hi ,\n\nI'd love to hear your feedback! Click on the stars below to rate our service.\n\n"
    "Kind Regards,\nJackie\nGlamnetic Management\n\n"
    "P.S. If you're reading this and haven't received our reply, please check your spam folder!"
)


def test_csat_auto_reply_does_not_advance_to_replied(tmp_path):
    led = pitched_ledger(tmp_path, ["glamnetic.com"])
    w = watcher(led, [Email("support@glamnetic.com",
                            "Re: Hey, saw you don't have an AI chatbot on your site", GLAMNETIC_CSAT)])
    results = w.poll()
    assert led.get_stage("glamnetic.com") == "Pitched"   # auto-reply is noise, not a real reply
    assert results == [(results[0][0], None)]


def test_human_reply_from_pitched_brand_still_advances(tmp_path):
    # Conservatism guard: the auto-reply filter must NOT swallow a genuine human reply.
    led = pitched_ledger(tmp_path, ["glamnetic.com"])
    w = watcher(led, [Email("founder@glamnetic.com", "Re: your message",
                            "Sure, how much would this cost per month?")])
    w.poll()
    assert led.get_stage("glamnetic.com") == "Replied"
