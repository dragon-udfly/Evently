import json

from app.models import AgentMessage, AgentState, Notification
from tests.helpers import book, make_event, make_user, make_venue


def test_one_booking_is_traceable_across_agents_by_conversation_id(db):
	ev = make_event(db, make_venue(db))
	u = make_user(db)
	r = book(db, u, ev, qty=2)
	msgs = db.query(AgentMessage).filter_by(conversation_id=r.conversation_id).order_by(AgentMessage.id).all()
	senders = {m.sender for m in msgs}
	assert {"BookingAgent", "TicketAgent"} <= senders
	assert {"REQUEST", "AGREE", "INFORM"} <= {m.performative for m in msgs}
	assert any(m.receiver == "*" and json.loads(m.content)["topic"] == "booking_confirmed" for m in msgs)


def test_notification_agent_reacts_to_broadcast_and_tells_the_right_user(db):
	ev = make_event(db, make_venue(db))
	buyer, other = make_user(db), make_user(db)
	book(db, buyer, ev)
	assert db.query(Notification).filter_by(user_id=buyer.id).count() == 1
	assert db.query(Notification).filter_by(user_id=other.id).count() == 0
	assert "confirmed" in db.query(Notification).first().message


def test_agent_beliefs_are_persisted_in_the_database(db):
	ev = make_event(db, make_venue(db))
	book(db, make_user(db), ev, qty=3)
	sold = db.get(AgentState, ("BookingAgent", "tickets_sold"))
	issued = db.get(AgentState, ("TicketAgent", "tickets_issued"))
	assert sold.value == "3" and issued.value == "3"


def test_refusals_always_carry_a_reason(db):
	ev = make_event(db, make_venue(db))
	r = book(db, make_user(db), ev, qty=99)
	assert r.performative == "REFUSE" and r.content["reason"]

