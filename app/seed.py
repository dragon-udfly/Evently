from datetime import timedelta

from sqlalchemy import select

from .config import now
from .database import SessionLocal
from .models import Event, TicketCategory, User, Venue
from .security import hash_password

DEMO_USERS = [("Admin", "admin@eventsphere.test", "Admin#12345", "admin"),
              ("Gate Staff", "staff@eventsphere.test", "Staff#12345", "staff"),
              ("Alice Attendee", "attendee@eventsphere.test", "Attendee#12345", "attendee")]


def seed():
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)):
            return
        for name, email, pw, role in DEMO_USERS:
            db.add(User(name=name, email=email, password_hash=hash_password(pw), role=role))
        hall = Venue(name="Main Auditorium", location="Main Campus, Block A", capacity=300, hourly_rate=8000,
                     description="Tiered seating, stage and AV.", open_for_hire=True)
        room = Venue(name="Seminar Room 1", location="Science Faculty, 2nd floor", capacity=40, hourly_rate=2500,
                     description="Projector and whiteboard.", open_for_hire=True)
        court = Venue(name="Open Courtyard", location="Central Courtyard", capacity=150, hourly_rate=4000,
                      description="Outdoor space for receptions.", open_for_hire=True)
        db.add_all([hall, room, court])
        db.flush()
        d = now().replace(minute=0, second=0)
        specs = [("Welcome Concert", "Concert", hall, 7, 18, 3, "Live music night.",
                  [("General", 1500, 100), ("VIP", 3000, 20)]),
                 ("Python Workshop", "Workshop", room, 3, 10, 3, "Hands-on beginner Python.",
                  [("Student", 500, 10), ("Public", 1000, 10)]),
                 ("AI Seminar", "Seminar", hall, 10, 14, 2, "Guest lecture on agents.", [("Free entry", 0, 50)])]
        for title, cat, venue, days, hour, hrs, desc, tickets in specs:
            start = (d + timedelta(days=days)).replace(hour=hour)
            ev = Event(title=title, category=cat, venue_id=venue.id, start=start, end=start + timedelta(hours=hrs),
                       description=desc, status="published")
            ev.categories = [TicketCategory(name=n, price=p, quantity=q) for n, p, q in tickets]
            db.add(ev)
        db.commit()
