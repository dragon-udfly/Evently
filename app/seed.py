from datetime import timedelta

from sqlalchemy import select

from .config import now
from .database import SessionLocal
from .models import Event, TicketCategory, User, Venue
from .security import hash_password

DEMO_USERS = [("Admin", "admin@eventsphere.test", "Admin#12345", "admin"),
              ("Gate Staff", "staff@eventsphere.test", "Staff#12345", "staff"),
              ("Alice Attendee", "attendee@eventsphere.test", "Attendee#12345", "attendee")]

