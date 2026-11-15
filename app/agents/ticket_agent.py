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

    def h_void(self, db: Session, msg: Message) -> Message:
        res = db.execute(update(Ticket).where(Ticket.booking_id == int(msg.content["booking_id"]),
                                              Ticket.status == "valid").values(status="cancelled"))
        self.bump(db, "tickets_voided", res.rowcount or 0)
        return self.reply(msg, "AGREE", voided=res.rowcount or 0)

    def h_scan(self, db: Session, msg: Message) -> Message:
        code = str(msg.content["code"]).strip()
        event_id = int(msg.content["event_id"])
        t = db.scalar(select(Ticket).where(Ticket.code == code))
        if t is None:
            self.bump(db, "rejected_unknown")
            return self.reply(msg, "REFUSE", verdict="unknown", reason="Unknown ticket code")
        ev = db.get(Event, t.event_id)
        if t.event_id != event_id:
            self.bump(db, "rejected_wrong_event")
            return self.reply(msg, "REFUSE", verdict="wrong_event",
                              reason=f"Ticket is for a different event: '{ev.title}'")
        scans = self.bump(db, f"scans:{code}")
        if t.status == "cancelled" or ev.status == "cancelled":
            self.bump(db, "rejected_cancelled")
            return self.reply(msg, "REFUSE", verdict="cancelled", reason="Ticket or event was cancelled")
        if t.status == "used":
            self.bump(db, "rejected_used")
            if scans >= settings.suspicious_scan_threshold:
                self.broadcast(db, msg.conversation_id, "suspicious_scan", code=code[:6] + "...",
                               scans=scans, event=ev.title)
            return self.reply(msg, "REFUSE", verdict="already_used",
                              reason=f"Already used at {t.used_at:%H:%M} (scan #{scans})", scans=scans)
        opens = ev.start - timedelta(minutes=settings.checkin_opens_minutes)
        if now() < opens:
            return self.reply(msg, "REFUSE", verdict="too_early", reason=f"Check-in opens at {opens:%d %b %H:%M}")
        if now() > ev.end:
            return self.reply(msg, "REFUSE", verdict="too_late", reason="Event has ended")
        res = db.execute(update(Ticket).where(Ticket.id == t.id, Ticket.status == "valid")
                         .values(status="used", used_at=now()))
        if res.rowcount == 0:  # lost a race with a simultaneous scan
            return self.reply(msg, "REFUSE", verdict="already_used", reason="Already used (simultaneous scan)")
        self.bump(db, "admitted")
        return self.reply(msg, "AGREE", verdict="admit", reason="Admit", event=ev.title)
