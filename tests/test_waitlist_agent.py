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

