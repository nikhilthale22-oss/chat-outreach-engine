"""Server-ACK confirm (ADR-0009): 'delivered' means the vendor's OWN server sent a receipt, not that
our screen looked right. Tidio's receipt is a socket.io ack frame `[true,{"id":<serverId>}]`; Help
Scout's is a POST 201 to its /conversations endpoint. These lock the receipt patterns + the confirm
logic so a submitted-looking send with NO server receipt is never called delivered (the raincaper bug).
"""
import json

from chat_outreach_engine.adapters.chatra import CHATRA
from chat_outreach_engine.adapters.helpscout import HELPSCOUT
from chat_outreach_engine.adapters.livechat import LIVECHAT
from chat_outreach_engine.adapters.tidio import TIDIO
from chat_outreach_engine.widget_driver import VendorConfig, WidgetDriver


# ----- the receipt patterns are wired on the two calibrated vendors -----

def test_tidio_has_a_websocket_receipt_pattern_helpscout_an_http_one():
    assert TIDIO.ack_frame_re and TIDIO.ack_response_re is None
    assert HELPSCOUT.ack_response_re and HELPSCOUT.ack_frame_re is None


def test_other_vendors_have_no_receipt_pattern_so_they_are_untouched():
    # A vendor with neither pattern set keeps its old confirm behaviour (no accidental strictening).
    plain = VendorConfig(
        vendor="x", widget_scope=None, ready_predicate="1", ready_fallback_predicate="1",
        ready_timeout_ms=1, not_ready_detail="no", open_js="", entry_labels=(),
        email_strategy="none", email_api_js=None, confirm_strategy="dom_echo",
        confirm_frame_marker=None,
    )
    assert plain.ack_frame_re is None and plain.ack_response_re is None


# ----- the real Tidio receipt frame matches; near-misses do not -----

def test_tidio_receipt_regex_matches_the_real_server_ack_frame():
    import re
    r = re.compile(TIDIO.ack_frame_re)
    assert r.search('4314[true,{"id":10336856193}]')          # the captured live server ack
    assert r.search('43[true,{"id": 42}]')                    # tolerant of a space after id:
    assert not r.search('4214["visitorNewMessage",{"message":"hi","messageId":"uuid"}]')  # OUR send
    assert not r.search('43[true,{}]')                        # an ack with no stored id
    assert not r.search('42["visitorIsTyping",{"message":"hi"}]')


def test_helpscout_receipt_regex_matches_the_conversation_endpoint():
    import re
    r = re.compile(HELPSCOUT.ack_response_re)
    assert r.search("https://beaconapi.helpscout.net/v1/abc-123/conversations")
    assert not r.search("https://beaconapi.helpscout.net/v1/abc-123/time")     # a GET config call
    assert not r.search("https://raincaper.com/api/collect")


# ----- _ack_receipt: captured receipts -> (delivered, detail-with-proof) -----

def test_ack_receipt_reads_the_server_id_from_a_ws_frame():
    ok, detail = WidgetDriver._ack_receipt([], ['4314[true,{"id":10336856193}]'])
    assert ok and detail == "delivered_ack:10336856193"


def test_ack_receipt_reads_the_status_from_an_http_receipt():
    ok, detail = WidgetDriver._ack_receipt([(201, "https://beaconapi.helpscout.net/v1/x/conversations")], [])
    assert ok and detail == "delivered_ack:201"


def test_ack_receipt_is_not_delivered_with_no_receipt():
    ok, detail = WidgetDriver._ack_receipt([], [])
    assert ok is False and detail == ""


# ----- _confirmed for wire_token: server receipt required at the final check, sent-frame fallback -----

def test_wire_token_confirmed_requires_the_server_receipt_when_supplied():
    d = WidgetDriver(TIDIO)
    # final check passes ack_ws: present -> delivered, empty -> NOT delivered (even if we "sent")
    assert d._confirmed(None, None, [], "flows", ack_ws=['[true,{"id":7}]']) is True
    assert d._confirmed(None, None, ['visitorNewMessage ... flows'], "flows", ack_ws=[]) is False


def test_wire_token_confirmed_falls_back_to_sent_frame_when_ack_ws_absent():
    # intermediate nudge checks don't pass ack_ws; they use the sent-frame signal so gate logic is
    # unchanged. A sent visitorNewMessage frame carrying the token still reads as sent there.
    d = WidgetDriver(TIDIO)
    sent = ['4214["visitorNewMessage",{"message":"I made 8 email flows","messageId":"u"}]']
    assert d._confirmed(None, None, sent, "flows", ack_ws=None) is True
    assert d._confirmed(None, None, [], "flows", ack_ws=None) is False


# ----- LiveChat: the receipt is a start_chat "response" frame with a non-empty event_ids -----

def test_livechat_uses_the_server_receipt_not_a_screen_echo():
    assert LIVECHAT.confirm_strategy == "wire_token" and LIVECHAT.ack_frame_re

def test_livechat_receipt_regex_matches_a_stored_event_only():
    import re
    r = re.compile(LIVECHAT.ack_frame_re)
    # the real captured frame (beautiesltd, online): the server assigned an event id to our message
    stored = ('{"request_id":"jk61no9wy5","action":"start_chat","type":"response","payload":'
              '{"chat_id":"TI0DVBCS8O","thread_id":"TI0DVBCS9O","event_ids":["TI0DVBCS9O_1"]},"success":true}')
    assert r.search(stored)
    # a chat opened with NO stored event, and a plain customer update, are NOT delivery receipts
    assert not r.search('{"action":"start_chat","type":"response","payload":{"event_ids":[]},"success":true}')
    assert not r.search('{"request_id":"x","action":"update_customer","type":"response","payload":{},"success":true}')


# ----- Chatra: the receipt is a DDP "Messages added" echo carrying OUR text (SockJS-escaped) -----

def _ddp(obj):
    """Reproduce a Chatra ws frame exactly as it arrives: a SockJS array wrapping a compact JSON
    string, so the inner quotes/backslashes are escaped (what page.on('framereceived') hands us).
    Chatra's real frames are compact (no spaces), so mirror that."""
    compact = json.dumps(obj, separators=(",", ":"))
    return "a[" + json.dumps(compact) + "]"

_CHATRA_OURS = _ddp({"msg": "added", "collection": "Messages", "id": "8yBFpT29THwFXrN3B",
                     "fields": {"clientId": "u7c", "ready": True, "createdAt": 1784373594822,
                                "message": "I made 8 email flows - see my calendar", "saved": True}})
_CHATRA_BOT = _ddp({"msg": "added", "collection": "Messages", "id": "jAfQNyhwQACsrEwRw",
                    "fields": {"type": "bot", "messageKeys": ["startOffline_required"], "saved": True}})


def test_chatra_regex_captures_messages_frames_through_the_sockjs_escaping():
    import re
    r = re.compile(CHATRA.ack_frame_re)
    assert r.search(_CHATRA_OURS)      # escaped \"collection\":\"Messages\" still matches
    assert r.search(_CHATRA_BOT)       # bot frames share the collection - captured, then token-filtered

def test_chatra_frame_ack_is_token_scoped_so_only_our_stored_message_counts():
    token = "calendar"
    # the full captured set (ours + bot) confirms; a bot-only set does NOT (no token in it)
    assert WidgetDriver._frame_ack([_CHATRA_BOT, _CHATRA_OURS], token) is True
    assert WidgetDriver._frame_ack([_CHATRA_BOT], token) is False

def test_frame_ack_needs_both_a_token_and_a_frame():
    assert WidgetDriver._frame_ack([], "calendar") is False
    assert WidgetDriver._frame_ack([_CHATRA_OURS], None) is False
    assert WidgetDriver._frame_ack(None, "calendar") is False
