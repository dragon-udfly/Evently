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
