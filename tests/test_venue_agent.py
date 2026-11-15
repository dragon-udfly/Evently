from datetime import timedelta

from app.models import HireRequest, Notification
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


def test_weekend_and_peak_pricing(db):
	v = make_venue(db, rate=1000)
	u = make_user(db)
	sat = next_slot(5, 10)
	r = send(db, "VenueAgent", "hire_request", user_id=u.id, venue_id=v.id, start=sat.isoformat(),
			 end=(sat + timedelta(hours=1)).isoformat(), guests=10, purpose="Party")
	assert r.content["price"] == 1250
	wed_peak = next_slot(2, 17)
	r = send(db, "VenueAgent", "hire_request", user_id=u.id, venue_id=v.id, start=wed_peak.isoformat(),
			 end=(wed_peak + timedelta(hours=1)).isoformat(), guests=10, purpose="Dinner")
	assert r.content["price"] == 1150


def test_large_group_is_escalated_to_admin_and_admin_can_approve(db):
	v = make_venue(db, capacity=100)
	u, admin = make_user(db), make_user(db, "admin")
	start = next_slot(2, 10)
	r = send(db, "VenueAgent", "hire_request", user_id=u.id, venue_id=v.id, start=start.isoformat(),
			 end=(start + timedelta(hours=2)).isoformat(), guests=90, purpose="Conference")
	assert r.performative == "INFORM" and r.content["decision"] == "escalate"
	assert db.query(Notification).filter_by(audience="admin").count() == 1
	d = send(db, "VenueAgent", "decide_hire", hire_id=r.content["hire_id"], decision="approve")
	assert d.performative == "AGREE" and db.get(HireRequest, r.content["hire_id"]).status == "confirmed"


def test_clash_returns_propose_with_usable_alternatives(db):
	v1 = make_venue(db, name="A")
	make_venue(db, name="B")
	u = make_user(db)
	start = next_slot(2, 10)
	args = dict(user_id=u.id, venue_id=v1.id, start=start.isoformat(),
				end=(start + timedelta(hours=2)).isoformat(), guests=10, purpose="Meeting")
	assert send(db, "VenueAgent", "hire_request", **args).performative == "AGREE"
	r = send(db, "VenueAgent", "hire_request", **args)
	assert r.performative == "PROPOSE" and r.content["reason"]
	alts = r.content["alternatives"]
	assert alts and {"venue_id", "start", "end", "price"} <= set(alts[0])
	assert any(a["kind"] == "other venue" for a in alts) and any(a["kind"] == "other time" for a in alts)

