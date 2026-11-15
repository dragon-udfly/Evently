import io
from datetime import datetime

import segno
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..agents.registry import request as ask
from ..config import now
from ..database import get_db
from ..models import Booking, Event, Notification, Ticket, TicketCategory, Venue, Waitlist
from ..policy import REFUND_POLICY, refund_pct
from ..schemas import EVENT_CATEGORIES
from ..security import csrf_protect, flash, get_current_user, login_required
from ..web import go, render

router = APIRouter()


@router.get("/")
def event_list(request: Request, q: str = "", category: str = "", venue_id: str = "", max_price: str = "",
               date_from: str = "", db: Session = Depends(get_db), user=Depends(get_current_user)):
    stmt = select(Event).where(Event.status == "published", Event.end > now()).order_by(Event.start)
    if q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Event.title.ilike(like), Event.description.ilike(like)))
    if category:
        stmt = stmt.where(Event.category == category)
    if venue_id.isdigit():
        stmt = stmt.where(Event.venue_id == int(venue_id))
    try:
        if max_price:
            stmt = stmt.where(Event.id.in_(select(TicketCategory.event_id).where(TicketCategory.price <= float(max_price))))
        if date_from:
            stmt = stmt.where(Event.start >= datetime.fromisoformat(date_from))
    except ValueError:
        flash(request, "Ignored an invalid price or date filter", "warning")
    events = db.scalars(stmt).all()
    venues = db.scalars(select(Venue).order_by(Venue.name)).all()
    return render(request, "events.html", user, events=events, venues=venues, categories=EVENT_CATEGORIES,
                  f=dict(q=q, category=category, venue_id=venue_id, max_price=max_price, date_from=date_from))


