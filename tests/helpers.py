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
