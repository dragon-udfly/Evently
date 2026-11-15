from threading import Thread

from sqlalchemy import func, select

from app.agents.registry import request as ask
from app.database import SessionLocal
from app.models import Booking, Ticket, TicketCategory
from tests.helpers import book, make_event, make_user, make_venue, send


def test_refuses_more_than_six_tickets_per_request(db):
    ev = make_event(db, make_venue(db), cats=(("General", 10.0, 50),))
    r = book(db, make_user(db), ev, qty=7)
    assert r.performative == "REFUSE" and "1 to 6" in r.content["reason"]


def test_per_user_limit_of_ten_tickets_per_event(db):
    ev = make_event(db, make_venue(db), cats=(("General", 10.0, 50),))
    u = make_user(db)
    assert book(db, u, ev, qty=6).performative == "AGREE"
    r = book(db, u, ev, qty=5)
    assert r.performative == "REFUSE" and "10" in r.content["reason"]


def test_never_oversells_when_many_book_at_once(db):
    ev = make_event(db, make_venue(db), cats=(("General", 10.0, 5),))
    cat_id, ev_id = ev.categories[0].id, ev.id
    uids = [make_user(db).id for _ in range(12)]
    results = []

    def worker(uid):
        with SessionLocal() as s:
            r = ask(s, f"user:{uid}", "BookingAgent", "book", user_id=uid, event_id=ev_id,
                    category_id=cat_id, quantity=1)
            s.commit()
            results.append(r.performative)

    threads = [Thread(target=worker, args=(u,)) for u in uids]
    [t.start() for t in threads]
    [t.join() for t in threads]
    with SessionLocal() as s:
        sold = s.get(TicketCategory, cat_id).sold
        tickets = s.scalar(select(func.count(Ticket.id)))
    assert results.count("AGREE") == 5 and results.count("REFUSE") == 7
    assert sold == 5 and tickets == 5


def test_last_seat_refusal_explains_and_offers_waitlist(db):
    ev = make_event(db, make_venue(db), cats=(("General", 10.0, 1),))
    assert book(db, make_user(db), ev).performative == "AGREE"
    r = book(db, make_user(db), ev)
    assert r.performative == "REFUSE" and r.content["left"] == 0 and r.content["can_waitlist"]


def test_payment_reference_and_unique_unguessable_tickets(db):
    ev = make_event(db, make_venue(db), cats=(("General", 25.0, 10),))
    r = book(db, make_user(db), ev, qty=3)
    assert r.content["payment_ref"].startswith("SIM-") and r.content["total"] == 75
    codes = [t.code for t in db.query(Ticket).all()]
    assert len(codes) == 3 == len(set(codes)) and all(len(c) >= 20 for c in codes)


def test_refund_follows_policy_tiers(db):
    v = make_venue(db)
    expected = {100: 100.0, 48: 50.0, 10: 0.0}  # hours before start -> refund of a 100.00 booking
    for hours, refund in expected.items():
        ev = make_event(db, v, hours_ahead=hours, duration=1, title=f"E{hours}", cats=(("G", 100.0, 5),))
        # use a distinct venue slot per event to keep the calendar rules out of this test
        v = make_venue(db, name=f"V{hours}")
        u = make_user(db)
        b = book(db, u, ev)
        r = send(db, "BookingAgent", "cancel", user_id=u.id, booking_id=b.content["booking_id"])
        assert r.performative == "AGREE" and r.content["refund"] == refund, hours


def test_cancel_refused_after_event_started(db):
    ev = make_event(db, make_venue(db), hours_ahead=1)
    u = make_user(db)
    b = book(db, u, ev)
    ev.start = ev.start.replace(year=ev.start.year - 1)
    ev.end = ev.end.replace(year=ev.end.year - 1)
    db.commit()
    assert send(db, "BookingAgent", "cancel", user_id=u.id, booking_id=b.content["booking_id"]).performative == "REFUSE"
