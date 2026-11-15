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


@router.get("/events/{event_id}")
def event_detail(event_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ev = db.get(Event, event_id)
    if ev is None or (ev.status == "draft" and not (user and user.role == "admin")):
        raise HTTPException(404, "Event not found")
    waits = []
    if user:
        for w in db.scalars(select(Waitlist).where(Waitlist.event_id == ev.id, Waitlist.user_id == user.id,
                                                   Waitlist.status.in_(["waiting", "held"]))):
            secs = max(int((w.hold_expires - now()).total_seconds()), 0) if w.hold_expires else 0
            waits.append((w, secs))
    on_sale = ev.status == "published" and now() < ev.start
    return render(request, "event_detail.html", user, ev=ev, waits=waits, on_sale=on_sale,
                  policy=REFUND_POLICY)


@router.post("/events/{event_id}/book", dependencies=[Depends(csrf_protect)])
def book(event_id: int, request: Request, category_id: int = Form(...), quantity: int = Form(1),
         hold_id: str = Form(""), user=Depends(login_required), db: Session = Depends(get_db)):
    reply = ask(db, f"user:{user.id}", "BookingAgent", "book", user_id=user.id, event_id=event_id,
                category_id=category_id, quantity=quantity, hold_id=int(hold_id) if hold_id.isdigit() else None)
    db.commit()
    if reply.performative == "AGREE":
        flash(request, f"Booked! Payment reference {reply.content['payment_ref']} (simulated).", "success")
        return go("/bookings")
    flash(request, reply.content.get("reason", "Booking failed"), "danger")
    return go(f"/events/{event_id}")


@router.post("/events/{event_id}/waitlist", dependencies=[Depends(csrf_protect)])
def join_waitlist(event_id: int, request: Request, category_id: int = Form(...), quantity: int = Form(1),
                  user=Depends(login_required), db: Session = Depends(get_db)):
    reply = ask(db, f"user:{user.id}", "WaitlistAgent", "join", user_id=user.id, event_id=event_id,
                category_id=category_id, quantity=quantity)
    db.commit()
    if reply.performative == "AGREE":
        flash(request, f"You are #{reply.content['position']} on the waitlist.", "success")
    else:
        flash(request, reply.content.get("reason", "Could not join"), "danger")
    return go(f"/events/{event_id}")


@router.post("/waitlist/{wid}/leave", dependencies=[Depends(csrf_protect)])
def leave_waitlist(wid: int, request: Request, user=Depends(login_required), db: Session = Depends(get_db)):
    w = db.get(Waitlist, wid)
    reply = ask(db, f"user:{user.id}", "WaitlistAgent", "leave", user_id=user.id, waitlist_id=wid)
    db.commit()
    flash(request, "Left the waitlist" if reply.performative == "AGREE" else reply.content["reason"], "info")
    return go(f"/events/{w.event_id}" if w else "/")


@router.get("/bookings")
def my_bookings(request: Request, user=Depends(login_required), db: Session = Depends(get_db)):
    rows = db.scalars(select(Booking).where(Booking.user_id == user.id, Booking.status != "failed")
                      .order_by(Booking.id.desc())).all()
    info = {b.id: (refund_pct(b.event), b.event.start > now()) for b in rows}
    return render(request, "bookings.html", user, bookings=rows, info=info, policy=REFUND_POLICY)


@router.post("/bookings/{bid}/cancel", dependencies=[Depends(csrf_protect)])
def cancel_booking(bid: int, request: Request, user=Depends(login_required), db: Session = Depends(get_db)):
    reply = ask(db, f"user:{user.id}", "BookingAgent", "cancel", user_id=user.id, booking_id=bid)
    db.commit()
    if reply.performative == "AGREE":
        flash(request, f"Cancelled. Refund {reply.content['refund']:.2f} ({reply.content['pct']}%).", "success")
    else:
        flash(request, reply.content.get("reason", "Could not cancel"), "danger")
    return go("/bookings")


def _own_ticket(code: str, user, db: Session) -> Ticket:
    t = db.scalar(select(Ticket).where(Ticket.code == code))
    if t is None or t.booking.user_id != user.id:
        raise HTTPException(404, "Ticket not found")
    return t


@router.get("/tickets/{code}")
def ticket_page(code: str, request: Request, user=Depends(login_required), db: Session = Depends(get_db)):
    t = _own_ticket(code, user, db)
    return render(request, "ticket.html", user, t=t, ev=db.get(Event, t.event_id))
