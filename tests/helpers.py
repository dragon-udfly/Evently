from datetime import timedelta

from app.agents.registry import request as ask
from app.config import now
from app.models import Event, TicketCategory, User, Venue
from app.security import hash_password

PASSWORD = "Pass#12345"


def make_user(db, role="attendee", email=None):
    n = db.query(User).count() + 1
    u = User(name=f"User {n}", email=email or f"user{n}@t.test", password_hash=hash_password(PASSWORD), role=role)
    db.add(u)
    db.commit()
    return u


def make_venue(db, capacity=100, hire=True, rate=1000.0, name="Hall"):
    v = Venue(name=name, location="Campus", capacity=capacity, hourly_rate=rate, open_for_hire=hire)
    db.add(v)
    db.commit()
    return v


def make_event(db, venue, hours_ahead=100, duration=2, cats=(("General", 100.0, 10),), status="published", title="Show"):
    start = (now() + timedelta(hours=hours_ahead)).replace(minute=0, second=0)
    ev = Event(title=title, category="Concert", venue_id=venue.id, start=start, end=start + timedelta(hours=duration),
               status=status)
    ev.categories = [TicketCategory(name=n, price=p, quantity=q) for n, p, q in cats]
    db.add(ev)
    db.commit()
    return ev


def send(db, receiver, action, sender="test", **content):
    reply = ask(db, sender, receiver, action, **content)
    db.commit()
    return reply


def book(db, user, ev, qty=1, cat=None, **extra):
    cat = cat or ev.categories[0]
    return send(db, "BookingAgent", "book", user_id=user.id, event_id=ev.id, category_id=cat.id, quantity=qty, **extra)
