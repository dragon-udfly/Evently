"""TicketAgent - goal: admit each ticket exactly once.

Rules
  T1  issue: one unguessable code (secrets.token_urlsafe(16)) per ticket.
  T2  scan verdicts, in order: unknown code -> refuse; wrong event -> refuse;
      cancelled (ticket or event) -> refuse; already used -> refuse;
      before check-in opens (2 h before start) or after event end -> refuse; else admit.
  T3  Admission is an atomic UPDATE ... WHERE status='valid', so two simultaneous scans admit once.
  T4  Beliefs: scans:<code> counts every scan of a code; 3 or more raises a suspicious_scan INFORM.
"""
import secrets
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..config import now, settings
from ..models import Event, Ticket
from .base import Agent
from .messages import Message


class TicketAgent(Agent):
    name = "TicketAgent"

    def h_issue(self, db: Session, msg: Message) -> Message:
        c = msg.content
        codes = []
        for _ in range(int(c["quantity"])):
            code = secrets.token_urlsafe(16)
            db.add(Ticket(booking_id=int(c["booking_id"]), event_id=int(c["event_id"]), code=code))
            codes.append(code)
        self.bump(db, "tickets_issued", len(codes))
        return self.reply(msg, "AGREE", codes=codes)

    