"""BookingAgent - goal: sell tickets fairly without overselling.

Rules
  B1  Quantity must be 1-6 per request.
  B2  Event must be published and not yet started.
  B3  One user may hold at most 10 confirmed tickets per event.
  B4  Capacity: an atomic  UPDATE ... SET sold = sold + q WHERE sold + q <= quantity.
      If 0 rows change, REFUSE with the number left (never oversell, even under concurrency).
  B5  A waitlist hold must belong to the user, be 'held' and not expired; it already reserved the seats.
  B6  Payment is simulated: reference SIM-XXXXXXXX.
  B7  If TicketAgent cannot issue tickets, the sale is compensated (seats released) and FAILURE is sent.
  B8  Refund on cancellation: >= 72 h before start 100%, 24-72 h 50%, < 24 h 0%; refuse after start.
  B9  Cancelled event: every booking refunded 100%, tickets voided, waitlist closed.
  B10 Freed seats are announced to WaitlistAgent (INFORM seats_freed).
"""
import secrets

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..config import now, settings
from ..models import Booking, Event, TicketCategory, Waitlist
from ..policy import refund_pct
from .base import Agent
from .messages import Message

class BookingAgent(Agent):
    name = "BookingAgent"

    def h_book(self, db: Session, msg: Message) -> Message:
        c = msg.content
        conv = msg.conversation_id
        uid, qty = int(c["user_id"]), int(c["quantity"])
        event = db.get(Event, int(c["event_id"]))
        cat = db.get(TicketCategory, int(c["category_id"]))
        if event is None or cat is None or cat.event_id != event.id:
            return self.reply(msg, "REFUSE", reason="Event or ticket category not found")
        if event.status != "published":
            return self.reply(msg, "REFUSE", reason="Event is not on sale")
        if now() >= event.start:
            return self.reply(msg, "REFUSE", reason="Event has already started; sales are closed")
        hold = None
        if c.get("hold_id"):
            hold = db.get(Waitlist, int(c["hold_id"]))
            if (hold is None or hold.user_id != uid or hold.status != "held" or hold.category_id != cat.id
                    or hold.hold_expires is None or hold.hold_expires <= now()):
                return self.reply(msg, "REFUSE", reason="Your seat hold is invalid or has expired")
            qty = hold.quantity
        if not 1 <= qty <= settings.max_tickets_per_request:
            return self.reply(msg, "REFUSE", reason=f"You can book 1 to {settings.max_tickets_per_request} tickets per request")
        owned = db.scalar(select(func.coalesce(func.sum(Booking.quantity), 0)).where(
            Booking.user_id == uid, Booking.event_id == event.id, Booking.status == "confirmed"))
        if owned + qty > settings.max_tickets_per_user_event:
            return self.reply(msg, "REFUSE", reason=f"Limit is {settings.max_tickets_per_user_event} tickets per person for one event (you have {owned})")
        if hold is None:
            res = db.execute(update(TicketCategory)
                             .where(TicketCategory.id == cat.id, TicketCategory.sold + qty <= TicketCategory.quantity)
                             .values(sold=TicketCategory.sold + qty))
            if res.rowcount == 0:
                db.refresh(cat)
                self.bump(db, "refused_sold_out")
                return self.reply(msg, "REFUSE", reason=f"Only {max(cat.left, 0)} ticket(s) left in '{cat.name}'",
                                  left=max(cat.left, 0), can_waitlist=True)
        booking = Booking(user_id=uid, event_id=event.id, category_id=cat.id, quantity=qty,
                          total=round(cat.price * qty, 2), payment_ref="SIM-" + secrets.token_hex(4).upper())
        db.add(booking)
        db.flush()
        if hold is not None:
            hold.status = "claimed"
        issued = self.tell(db, "TicketAgent", "REQUEST", conv, action="issue",
                           booking_id=booking.id, event_id=event.id, quantity=qty)
        if issued is None or issued.performative != "AGREE":  # B7 compensation
            db.execute(update(TicketCategory).where(TicketCategory.id == cat.id).values(sold=TicketCategory.sold - qty))
            booking.status = "failed"
            return self.reply(msg, "FAILURE", reason="Ticket issuing failed; you were not charged")
        self.bump(db, "tickets_sold", qty)
        self.broadcast(db, conv, "booking_confirmed", user_id=uid, booking_id=booking.id, event=event.title,
                       quantity=qty, total=booking.total, payment_ref=booking.payment_ref)
        return self.reply(msg, "AGREE", booking_id=booking.id, payment_ref=booking.payment_ref,
                          total=booking.total, quantity=qty)

    