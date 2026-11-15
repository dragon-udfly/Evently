"""NotificationAgent - goal: tell the right person what affects them.

Rules (reactive: it listens to every broadcast INFORM)
  N1  booking_confirmed / booking_cancelled / event_cancelled -> the booking user.
  N2  hold_offered / hold_expired -> the waiting user.
  N3  hire_confirmed / hire_decided -> the requester; hire_escalated -> admins.
  N4  suspicious_scan -> admins.
Unknown topics are ignored.
"""
from sqlalchemy.orm import Session

from ..models import Notification
from .base import Agent
from .messages import Message


class NotificationAgent(Agent):
    name = "NotificationAgent"

    def _add(self, db: Session, text: str, user_id: int | None = None, audience: str = "user"):
        db.add(Notification(user_id=user_id, audience=audience, message=text[:500]))
        self.bump(db, "notifications_sent")

    def h_booking_confirmed(self, db: Session, msg: Message):
        c = msg.content
        self._add(db, f"Booking #{c['booking_id']} confirmed: {c['quantity']} x {c['event']}. "
                      f"Paid {c['total']:.2f} (ref {c['payment_ref']}).", c["user_id"])

    def h_booking_cancelled(self, db: Session, msg: Message):
        c = msg.content
        self._add(db, f"Booking for {c['event']} cancelled. Refund {c['refund']:.2f} ({c['pct']}%).", c["user_id"])

    def h_event_cancelled(self, db: Session, msg: Message):
        c = msg.content
        if "user_id" in c:
            self._add(db, f"{c['event']} was cancelled. Full refund of {c['refund']:.2f} issued.", c["user_id"])

    def h_hold_offered(self, db: Session, msg: Message):
        c = msg.content
        self._add(db, f"Seats available! {c['quantity']} ticket(s) for {c['event']} held for you for "
                      f"{c['minutes']} minutes. Open the event page to claim.", c["user_id"])

    def h_hold_expired(self, db: Session, msg: Message):
        c = msg.content
        self._add(db, f"Your seat hold for {c['event']} expired and was passed on.", c["user_id"])

    def h_hire_confirmed(self, db: Session, msg: Message):
        c = msg.content
        self._add(db, f"Hire #{c['hire_id']} of {c['venue']} confirmed automatically. Price {c['price']:.2f}.", c["user_id"])

    def h_hire_escalated(self, db: Session, msg: Message):
        c = msg.content
        self._add(db, f"Hire request #{c['hire_id']} for {c['venue']} needs approval.", None, "admin")
        self._add(db, f"Hire #{c['hire_id']} of {c['venue']} sent to admin for approval.", c["user_id"])

    def h_hire_decided(self, db: Session, msg: Message):
        c = msg.content
        self._add(db, f"Hire #{c['hire_id']} of {c['venue']} was {c['decision']}. {c.get('note', '')}", c["user_id"])

   