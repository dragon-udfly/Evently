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


@router.get("/venues/{vid}/edit")
def venue_edit(vid: int, request: Request, user=Depends(admin_only), db: Session = Depends(get_db)):
    v = db.get(Venue, vid)
    if v is None:
        raise HTTPException(404, "Venue not found")
    return render(request, "admin/venues.html", user, venues=db.scalars(select(Venue).order_by(Venue.id)).all(), v=v)


@router.post("/venues", dependencies=CSRF)
@router.post("/venues/{vid}", dependencies=CSRF)
def venue_save(request: Request, vid: int | None = None, name: str = Form(""), location: str = Form(""),
               capacity: str = Form(""), description: str = Form(""), image_url: str = Form(""),
               hourly_rate: str = Form("0"), open_for_hire: str = Form(""),
               user=Depends(admin_only), db: Session = Depends(get_db)):
    try:
        data = _venue_from_form(name, location, capacity, description, image_url, hourly_rate, open_for_hire)
    except ValidationError as e:
        flash(request, first_error(e), "danger")
        return go(f"/admin/venues/{vid}/edit" if vid else "/admin/venues")
    v = db.get(Venue, vid) if vid else Venue()
    if v is None:
        raise HTTPException(404, "Venue not found")
    for k, val in data.model_dump().items():
        setattr(v, k, val)
    db.add(v)
    db.commit()
    flash(request, "Venue saved", "success")
    return go("/admin/venues")


# ---------------- events ----------------
def _form_ctx(db, ev=None, form=None):
    return dict(venues=db.scalars(select(Venue).order_by(Venue.name)).all(), categories=EVENT_CATEGORIES, ev=ev,
                form=form or {})


@router.get("/events")
def events(request: Request, user=Depends(admin_only), db: Session = Depends(get_db)):
    rows = db.scalars(select(Event).order_by(Event.start.desc())).all()
    return render(request, "admin/events.html", user, events=rows)


@router.get("/events/new")
def event_new(request: Request, user=Depends(admin_only), db: Session = Depends(get_db)):
    return render(request, "admin/event_form.html", user, locked=False, **_form_ctx(db))


@router.get("/events/{eid}/edit")
def event_edit(eid: int, request: Request, user=Depends(admin_only), db: Session = Depends(get_db)):
    ev = db.get(Event, eid)
    if ev is None:
        raise HTTPException(404, "Event not found")
    locked = db.scalar(select(func.count(Booking.id)).where(Booking.event_id == eid)) > 0
    return render(request, "admin/event_form.html", user, locked=locked, **_form_ctx(db, ev))


def _parse_event(title, category, venue_id, start, end, description, names, prices, qtys) -> EventIn:
    cats = [CategoryIn(name=n.strip(), price=p, quantity=q)
            for n, p, q in zip(names, prices, qtys) if n.strip()]
    return EventIn(title=title, category=category, venue_id=venue_id, start=start, end=end,
                   description=description, categories=cats)


@router.post("/events", dependencies=CSRF)
@router.post("/events/{eid}", dependencies=CSRF)
def event_save(request: Request, eid: int | None = None, title: str = Form(""), category: str = Form("Other"),
               venue_id: str = Form(""), start: str = Form(""), end: str = Form(""), description: str = Form(""),
               cat_name: list[str] = Form([]), cat_price: list[str] = Form([]), cat_qty: list[str] = Form([]),
               action: str = Form("draft"), user=Depends(admin_only), db: Session = Depends(get_db)):
    ev = db.get(Event, eid) if eid else None
    if eid and ev is None:
        raise HTTPException(404, "Event not found")
    locked = bool(ev) and db.scalar(select(func.count(Booking.id)).where(Booking.event_id == eid)) > 0
    try:
        if locked:  # bookings exist: ticket categories are frozen
            cat_name = [c.name for c in ev.categories]
            cat_price = [str(c.price) for c in ev.categories]
            cat_qty = [str(c.quantity) for c in ev.categories]
        data = _parse_event(title, category, venue_id, start, end, description, cat_name, cat_price, cat_qty)
    except ValidationError as e:
        flash(request, first_error(e), "danger")
        return go(f"/admin/events/{eid}/edit" if eid else "/admin/events/new")
    if ev is not None and ev.status == "cancelled":
        flash(request, "A cancelled event cannot be edited", "danger")
        return go("/admin/events")
    # VenueAgent decides whether the slot and ticket total are acceptable (rules V1-V3)
    reply = ask(db, f"admin:{user.id}", "VenueAgent", "check_slot", venue_id=data.venue_id,
                start=data.start.isoformat(), end=data.end.isoformat(),
                total_tickets=sum(c.quantity for c in data.categories), event_id=eid)
    db.commit()  # keeps the message log even when refused
    if reply.performative != "AGREE":
        flash(request, "VenueAgent refused: " + reply.content.get("reason", "slot unavailable"), "danger")
        return go(f"/admin/events/{eid}/edit" if eid else "/admin/events/new")
    if ev is None:
        ev = Event()
    for k in ("title", "category", "venue_id", "start", "end", "description"):
        setattr(ev, k, getattr(data, k))
    if ev.status != "published":
        ev.status = "published" if action == "publish" else "draft"
    if not locked:
        ev.categories = [TicketCategory(name=c.name, price=c.price, quantity=c.quantity) for c in data.categories]
    db.add(ev)
    db.commit()
    flash(request, f"Event saved as {ev.status}", "success")
    return go("/admin/events")


@router.post("/events/{eid}/publish", dependencies=CSRF)
def event_publish(eid: int, request: Request, user=Depends(admin_only), db: Session = Depends(get_db)):
    ev = db.get(Event, eid)
    if ev is None or ev.status != "draft":
        flash(request, "Only a draft can be published", "danger")
        return go("/admin/events")
    reply = ask(db, f"admin:{user.id}", "VenueAgent", "check_slot", venue_id=ev.venue_id,
                start=ev.start.isoformat(), end=ev.end.isoformat(),
                total_tickets=sum(c.quantity for c in ev.categories), event_id=ev.id)
    if reply.performative == "AGREE":
        ev.status = "published"
        flash(request, "Event published", "success")
    else:
        flash(request, "VenueAgent refused: " + reply.content.get("reason", ""), "danger")
    db.commit()
    return go("/admin/events")


@router.post("/events/{eid}/cancel", dependencies=CSRF)
def event_cancel(eid: int, request: Request, user=Depends(admin_only), db: Session = Depends(get_db)):
    reply = ask(db, f"admin:{user.id}", "BookingAgent", "cancel_event", event_id=eid)
    db.commit()
    if reply.performative == "AGREE":
        flash(request, f"Event cancelled. {reply.content['refunded_bookings']} booking(s) refunded "
                       f"({reply.content['total_refunded']:.2f}).", "success")
    else:
        flash(request, reply.content.get("reason", "Could not cancel"), "danger")
    return go("/admin/events")


# ---------------- private hire ----------------
@router.get("/hires")
def hires(request: Request, user=Depends(admin_only), db: Session = Depends(get_db)):
    rows = db.scalars(select(HireRequest).order_by(HireRequest.status.desc(), HireRequest.id.desc())).all()
    return render(request, "admin/hires.html", user, hires=rows)


@router.post("/hires/{hid}/{decision}", dependencies=CSRF)
def hire_decide(hid: int, decision: str, request: Request, note: str = Form(""),
                user=Depends(admin_only), db: Session = Depends(get_db)):
    if decision not in ("approve", "reject"):
        raise HTTPException(404, "Unknown decision")
    reply = ask(db, f"admin:{user.id}", "VenueAgent", "decide_hire", hire_id=hid, decision=decision, note=note)
    db.commit()
    ok = reply.performative == "AGREE"
    flash(request, f"Hire {'approved' if decision == 'approve' else 'rejected'}" if ok else reply.content["reason"],
          "success" if ok else "danger")
    return go("/admin/hires")
