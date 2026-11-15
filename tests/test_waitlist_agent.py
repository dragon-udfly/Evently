from datetime import timedelta

from app.agents.scheduler import run_sweep
from app.config import now
from app.database import SessionLocal
from app.models import Notification, TicketCategory, Waitlist
from tests.helpers import book, make_event, make_user, make_venue, send


def full_event(db):
	ev = make_event(db, make_venue(db), cats=(("General", 10.0, 2),))
	owner = make_user(db)
	b = book(db, owner, ev, qty=2)
	return ev, owner, b.content["booking_id"]


def join(db, user, ev, qty=2):
	return send(db, "WaitlistAgent", "join", user_id=user.id, event_id=ev.id, category_id=ev.categories[0].id, quantity=qty)


def test_cannot_join_while_tickets_are_available(db):
	ev = make_event(db, make_venue(db))
	r = join(db, make_user(db), ev, 1)
	assert r.performative == "REFUSE" and "available" in r.content["reason"]


def test_freed_seats_are_held_for_first_in_line_then_claimed(db):
	ev, owner, bid = full_event(db)
	first, second = make_user(db), make_user(db)
	assert join(db, first, ev).content["position"] == 1
	assert join(db, second, ev).content["position"] == 2
	send(db, "BookingAgent", "cancel", user_id=owner.id, booking_id=bid)
	held = db.query(Waitlist).filter_by(user_id=first.id).one()
	db.refresh(held)
	assert held.status == "held" and held.hold_expires > now()
	assert db.query(Waitlist).filter_by(user_id=second.id).one().status == "waiting"
	assert db.query(Notification).filter(Notification.user_id == first.id, Notification.message.contains("held")).count() == 1
	# seats are reserved: a stranger cannot take them
	assert book(db, make_user(db), ev, qty=1).performative == "REFUSE"
	# the holder claims them
	r = book(db, first, ev, qty=2, hold_id=held.id)
	assert r.performative == "AGREE"
	db.refresh(held)
	assert held.status == "claimed"
	assert db.get(TicketCategory, ev.categories[0].id).sold == 2


def test_sweep_expires_unclaimed_hold_and_reoffers_to_next(db):
	ev, owner, bid = full_event(db)
	first, second = make_user(db), make_user(db)
	join(db, first, ev)
	join(db, second, ev)
	send(db, "BookingAgent", "cancel", user_id=owner.id, booking_id=bid)
	h1 = db.query(Waitlist).filter_by(user_id=first.id).one()
	h1.hold_expires = now() - timedelta(minutes=1)  # time passes with no action by the user
	db.commit()
	run_sweep()  # what the scheduler does every 30 s
	with SessionLocal() as s:
		assert s.query(Waitlist).filter_by(user_id=first.id).one().status == "expired"
		h2 = s.query(Waitlist).filter_by(user_id=second.id).one()
		assert h2.status == "held" and h2.hold_expires > now()
		assert s.get(TicketCategory, ev.categories[0].id).sold == 2
		assert s.query(Notification).filter(Notification.user_id == first.id, Notification.message.contains("expired")).count() == 1

