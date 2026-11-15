"""WaitlistAgent - goal: pass freed seats to waiting customers.

Rules
  W1  join: refuse if the category still has enough seats (book directly) or the user is already queued.
  W2  Freed seats go to the longest-waiting entry whose quantity fits (first come, first served;
      an entry too big for the free seats is skipped, not blocking the queue).
  W3  A hold reserves the seats immediately (counted in 'sold') for HOLD_MINUTES.
  W4  PROACTIVE: the scheduler sends INFORM sweep every 30 s; expired holds are released,
      the user is told, and the seats are re-offered to the next in line.
  W5  When an event is cancelled all queue entries are closed.
"""
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from datetime import timedelta

from ..config import now, settings
from ..models import Event, TicketCategory, Waitlist
from .base import Agent
from .messages import Message


class WaitlistAgent(Agent):
    name = "WaitlistAgent"

    def h_join(self, db: Session, msg: Message) -> Message:
        c = msg.content
        uid, qty = int(c["user_id"]), int(c["quantity"])
        cat = db.get(TicketCategory, int(c["category_id"]))
        ev = db.get(Event, int(c["event_id"]))
        if cat is None or ev is None or cat.event_id != ev.id or ev.status != "published" or ev.start <= now():
            return self.reply(msg, "REFUSE", reason="Event is not open for the waitlist")
        if not 1 <= qty <= settings.max_tickets_per_request:
            return self.reply(msg, "REFUSE", reason=f"Choose 1 to {settings.max_tickets_per_request} tickets")
        if cat.left >= qty:
            return self.reply(msg, "REFUSE", reason="Tickets are still available - please book directly")
        dup = db.scalar(select(Waitlist).where(Waitlist.user_id == uid, Waitlist.category_id == cat.id,
                                               Waitlist.status.in_(["waiting", "held"])))
        if dup:
            return self.reply(msg, "REFUSE", reason="You are already on this waitlist")
        w = Waitlist(event_id=ev.id, category_id=cat.id, user_id=uid, quantity=qty)
        db.add(w)
        db.flush()
        pos = len(db.scalars(select(Waitlist.id).where(Waitlist.category_id == cat.id, Waitlist.status == "waiting",
                                                       Waitlist.id <= w.id)).all())
        self.bump(db, "joined")
        return self.reply(msg, "AGREE", waitlist_id=w.id, position=pos)

    def h_leave(self, db: Session, msg: Message) -> Message:
        w = db.get(Waitlist, int(msg.content["waitlist_id"]))
        if w is None or w.user_id != int(msg.content["user_id"]) or w.status not in ("waiting", "held"):
            return self.reply(msg, "REFUSE", reason="Nothing to leave")
        was_held = w.status == "held"
        w.status = "left"
        if was_held:
            self._release(db, w)
            self._offer(db, w.category_id, msg.conversation_id)
        return self.reply(msg, "AGREE")

    