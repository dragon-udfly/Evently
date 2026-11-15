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

    