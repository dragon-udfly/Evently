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
from datetime import datetime, timedelta


def _dt(v) -> datetime:
    return v if isinstance(v, datetime) else datetime.fromisoformat(str(v))


def fmt(d: datetime) -> str:
    return d.strftime("%d %b %H:%M")


