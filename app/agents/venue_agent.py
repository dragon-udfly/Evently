"""VenueAgent - goal: keep every venue's calendar free of clashes.

Decision rules
  V1  Refuse a slot if end <= start.
  V2  Refuse an event whose total tickets exceed venue capacity.
  V3  Refuse a slot that overlaps another non-cancelled event or a confirmed/pending hire,
      counting a 30 minute turnaround buffer on both sides.
  H1  Refuse hire if venue is not open for private hire, start is in the past,
      duration is over 12 h, or guests exceed capacity.
  H2  Clash -> PROPOSE up to 3 alternative times (same venue, +-1..24 h) and
      up to 3 other venues free at the requested time.
  H3  Price = hourly rate x hours; x1.25 on weekends, x1.15 for 17:00-22:00 (peak); both stack.
  H4  Routine (<= 4 h and guests <= 80% of capacity) -> AGREE (confirmed automatically);
      otherwise -> INFORM decision=escalate (pending admin approval).
  H5  Admin decision: approving re-checks for clashes first.
"""
import math
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import now, settings
from ..models import Event, HireRequest, Venue
from .base import Agent
from .messages import Message


def _dt(v) -> datetime:
    return v if isinstance(v, datetime) else datetime.fromisoformat(str(v))


def fmt(d: datetime) -> str:
    return d.strftime("%d %b %H:%M")


class VenueAgent(Agent):
    name = "VenueAgent"

    # ---------- calendar ----------
    def conflicts(self, db: Session, venue_id: int, start: datetime, end: datetime,
                  exclude_event_id: int | None = None, exclude_hire_id: int | None = None) -> list[str]:
        buf = timedelta(minutes=settings.venue_buffer_minutes)
        lo, hi = start - buf, end + buf
        out = []
        for e in db.scalars(select(Event).where(
                Event.venue_id == venue_id, Event.status != "cancelled", Event.start < hi, Event.end > lo)):
            if e.id != exclude_event_id:
                out.append(f"event '{e.title}' ({fmt(e.start)}-{fmt(e.end)})")
        for h in db.scalars(select(HireRequest).where(
                HireRequest.venue_id == venue_id, HireRequest.status.in_(["confirmed", "pending"]),
                HireRequest.start < hi, HireRequest.end > lo)):
            if h.id != exclude_hire_id:
                out.append(f"private hire ({fmt(h.start)}-{fmt(h.end)})")
        return out

    def quote(self, venue: Venue, start: datetime, end: datetime) -> tuple[float, str]:
        total, t, notes = 0.0, start, set()
        while t < end:
            step = min(timedelta(minutes=30), end - t)
            mult = 1.0
            if t.weekday() >= 5:
                mult *= settings.weekend_multiplier
                notes.add("weekend x1.25")
            if settings.peak_from_hour <= t.hour < settings.peak_to_hour:
                mult *= settings.peak_multiplier
                notes.add("peak x1.15")
            total += venue.hourly_rate * (step.total_seconds() / 3600) * mult
            t += step
        return round(total, 2), ", ".join(sorted(notes)) or "standard rate"

    def alternatives(self, db: Session, venue: Venue, start: datetime, end: datetime, guests: int) -> list[dict]:
        dur, out = end - start, []
        for k in range(1, 25):
            for off in (k, -k):
                s = start + timedelta(hours=off)
                if s <= now() or len(out) >= 3:
                    continue
                if not self.conflicts(db, venue.id, s, s + dur):
                    price, _ = self.quote(venue, s, s + dur)
                    out.append({"venue_id": venue.id, "venue_name": venue.name, "start": s.isoformat(),
                                "end": (s + dur).isoformat(), "price": price, "kind": "other time"})
            if len(out) >= 3:
                break
        others = 0
        for v in db.scalars(select(Venue).where(Venue.open_for_hire.is_(True), Venue.id != venue.id)):
            if v.capacity >= guests and not self.conflicts(db, v.id, start, end) and others < 3:
                price, _ = self.quote(v, start, end)
                out.append({"venue_id": v.id, "venue_name": v.name, "start": start.isoformat(),
                            "end": end.isoformat(), "price": price, "kind": "other venue"})
                others += 1
        return out

    