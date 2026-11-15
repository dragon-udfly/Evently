import json

from app.models import AgentMessage
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

