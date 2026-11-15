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


def test_unknown_wrong_event_and_cancelled_are_rejected_with_reasons(db):
	ev, u, b, code = setup_ticket(db)
	other = make_event(db, make_venue(db, name="Other"), hours_ahead=1, title="Other show")
	assert scan(db, "no-such-code", ev).content["verdict"] == "unknown"
	wrong = scan(db, code, other)
	assert wrong.content["verdict"] == "wrong_event" and "Show" in wrong.content["reason"]
	send(db, "BookingAgent", "cancel", user_id=u.id, booking_id=b.content["booking_id"])
	assert scan(db, code, ev).content["verdict"] == "cancelled"


def test_checkin_closed_before_window_opens(db):
	ev, _, _, code = setup_ticket(db, hours_ahead=100)
	r = scan(db, code, ev)
	assert r.performative == "REFUSE" and r.content["verdict"] == "too_early"

