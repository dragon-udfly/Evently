from app.models import Ticket
from tests.helpers import book, make_event, make_user, make_venue, send


def setup_ticket(db, hours_ahead=1):
	ev = make_event(db, make_venue(db), hours_ahead=hours_ahead)
	u = make_user(db)
	b = book(db, u, ev)
	return ev, u, b, db.query(Ticket).first().code


def scan(db, code, ev):
	return send(db, "TicketAgent", "scan", sender="staff:1", code=code, event_id=ev.id)


def test_ticket_admitted_once_then_rejected(db):
	ev, _, _, code = setup_ticket(db)
	first = scan(db, code, ev)
	assert first.performative == "AGREE" and first.content["verdict"] == "admit"
	second = scan(db, code, ev)
	assert second.performative == "REFUSE" and second.content["verdict"] == "already_used"
	assert "Already used" in second.content["reason"]

