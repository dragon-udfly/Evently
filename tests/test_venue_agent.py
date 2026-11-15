from datetime import timedelta

from app.models import HireRequest
from tests.helpers import make_event, make_user, make_venue, next_slot, send


def slot(ev, start_offset_min, hours=1):
	s = ev.end + timedelta(minutes=start_offset_min)
	return s.isoformat(), (s + timedelta(hours=hours)).isoformat()


def test_refuses_overlap_and_respects_turnaround_buffer(db):
	v = make_venue(db)
	ev = make_event(db, v)
	s, e = slot(ev, 15)  # starts 15 min after the event ends: inside the 30 min buffer
	r = send(db, "VenueAgent", "check_slot", venue_id=v.id, start=s, end=e, total_tickets=10)
	assert r.performative == "REFUSE" and "clash" in r.content["reason"].lower()
	s, e = slot(ev, 30)  # exactly the buffer: allowed
	assert send(db, "VenueAgent", "check_slot", venue_id=v.id, start=s, end=e, total_tickets=10).performative == "AGREE"


def test_refuses_tickets_above_capacity_and_allows_editing_own_event(db):
	v = make_venue(db, capacity=50)
	ev = make_event(db, v)
	args = dict(venue_id=v.id, start=ev.start.isoformat(), end=ev.end.isoformat())
	assert send(db, "VenueAgent", "check_slot", total_tickets=51, **args).performative == "REFUSE"
	assert send(db, "VenueAgent", "check_slot", total_tickets=50, event_id=ev.id, **args).performative == "AGREE"


def test_routine_hire_is_confirmed_and_priced(db):
	v = make_venue(db, capacity=100, rate=1000)
	u = make_user(db)
	start = next_slot(2, 10)  # a Wednesday, off-peak
	r = send(db, "VenueAgent", "hire_request", user_id=u.id, venue_id=v.id, start=start.isoformat(),
			 end=(start + timedelta(hours=2)).isoformat(), guests=30, purpose="Farewell")
	assert r.performative == "AGREE" and r.content["decision"] == "confirmed" and r.content["price"] == 2000
	assert db.query(HireRequest).one().status == "confirmed"

