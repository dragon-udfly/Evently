import json

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..agents.registry import request as ask
from ..agents.scheduler import run_sweep
from ..database import get_db
from ..models import (AgentMessage, AgentState, Booking, Event, HireRequest, Notification, Ticket,
                      TicketCategory, Venue)
from ..schemas import EVENT_CATEGORIES, CategoryIn, EventIn, VenueIn, first_error
from ..security import csrf_protect, flash, require_role
from ..web import go, render

router = APIRouter(prefix="/admin")
admin_only = require_role("admin")
CSRF = [Depends(csrf_protect)]


# ---------------- dashboard ----------------
@router.get("")
def dashboard(request: Request, conv: str = "", user=Depends(admin_only), db: Session = Depends(get_db)):
    stats = []
    for ev in db.scalars(select(Event).where(Event.status != "draft").order_by(Event.start.desc())):
        def count(*status):
            return db.scalar(select(func.count(Ticket.id)).where(Ticket.event_id == ev.id, Ticket.status.in_(status)))
        revenue = db.scalar(select(func.coalesce(func.sum(Booking.total - Booking.refund_amount), 0)).where(
            Booking.event_id == ev.id, Booking.status.in_(["confirmed", "cancelled"])))
        stats.append(dict(ev=ev, sold=count("valid", "used"), checked_in=count("used"), revenue=float(revenue),
                          capacity=ev.venue.capacity, tickets=sum(c.quantity for c in ev.categories)))
    q = select(AgentMessage).order_by(AgentMessage.id.desc()).limit(150)
    if conv.strip():
        q = select(AgentMessage).where(AgentMessage.conversation_id == conv.strip()).order_by(AgentMessage.id)
    messages = db.scalars(q).all()
    beliefs = db.scalars(select(AgentState).order_by(AgentState.agent, AgentState.key).limit(60)).all()
    alerts = db.scalars(select(Notification).where(Notification.audience == "admin")
                        .order_by(Notification.id.desc()).limit(10)).all()
    pending = db.scalar(select(func.count(HireRequest.id)).where(HireRequest.status == "pending"))
    chart = json.dumps({"labels": [s["ev"].title for s in stats], "sold": [s["sold"] for s in stats],
                        "checked": [s["checked_in"] for s in stats]}).replace("<", "\u003c")
    return render(request, "admin/dashboard.html", user, stats=stats, messages=messages, beliefs=beliefs,
                  alerts=alerts, pending=pending, conv=conv, chart=chart)


@router.post("/sweep", dependencies=CSRF)
def manual_sweep(request: Request, user=Depends(admin_only)):
    run_sweep()
    flash(request, "WaitlistAgent sweep executed", "info")
    return go("/admin")


# ---------------- venues ----------------
def _venue_from_form(name, location, capacity, description, image_url, hourly_rate, open_for_hire) -> VenueIn:
    return VenueIn(name=name, location=location, capacity=capacity, description=description,
                   image_url=image_url, hourly_rate=hourly_rate, open_for_hire=bool(open_for_hire))


@router.get("/venues")
def venues(request: Request, user=Depends(admin_only), db: Session = Depends(get_db)):
    return render(request, "admin/venues.html", user, venues=db.scalars(select(Venue).order_by(Venue.id)).all(), v=None)
