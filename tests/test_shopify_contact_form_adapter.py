"""ShopifyContactFormAdapter delivers the Pitch through a store's native Shopify contact form (the
second delivery door). These tests lock the theme-robust field classification and the Shopify success
signal - the parts that must be right for the live submit to land. The live submit itself is proven by
a real run against the Arova mock store (visible testing), not mocked here.
"""
from chat_outreach_engine.adapters.shopify_contact_form import (
    CONTACT_PATHS,
    ShopifyContactFormAdapter,
    _field_role,
    _is_success,
)


def test_vendor_id():
    assert ShopifyContactFormAdapter.vendor == "shopify-contact-form"


def test_message_is_the_textarea_regardless_of_field_name():
    # theme names vary: contact[body] / contact[Comment] / contact[Message] - all are the textarea
    assert _field_role("textarea", "contact[body]", "") == "message"
    assert _field_role("textarea", "contact[Comment]", "") == "message"
    assert _field_role("textarea", "contact[Message]", "") == "message"


def test_email_classified_by_type_or_name_any_case():
    assert _field_role("input", "contact[email]", "email") == "email"
    assert _field_role("input", "contact[Email]", "text") == "email"   # name carries it
    assert _field_role("input", "whatever", "email") == "email"        # type carries it


def test_name_and_phone_roles_case_insensitive():
    assert _field_role("input", "contact[Name]", "text") == "name"
    assert _field_role("input", "contact[name]", "text") == "name"
    assert _field_role("input", "contact[phone]", "text") == "phone"
    assert _field_role("input", "x", "tel") == "phone"


def test_extra_fields_are_other_not_misclassified():
    assert _field_role("input", "contact[Order Number]", "text") == "other"
    assert _field_role("select", "contact[Reason]", "") == "other"


def test_success_from_shopify_posted_query():
    assert _is_success("https://shop.com/pages/contact?contact_posted=true", "") is True


def test_success_from_thank_you_text():
    assert _is_success("https://shop.com/pages/contact", "Thanks for contacting us! We'll get back to you soon.") is True


def test_not_success_when_no_signal():
    assert _is_success("https://shop.com/pages/contact", "Contact us using the form below.") is False


def test_contact_paths_lead_with_the_shopify_default():
    assert CONTACT_PATHS[0] == "/pages/contact"
