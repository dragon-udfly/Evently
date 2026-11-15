"""TicketAgent - goal: admit each ticket exactly once.

Rules
  T1  issue: one unguessable code (secrets.token_urlsafe(16)) per ticket.
  T2  scan verdicts, in order: unknown code -> refuse; wrong event -> refuse;
      cancelled (ticket or event) -> refuse; already used -> refuse;
      before check-in opens (2 h before start) or after event end -> refuse; else admit.
  T3  Admission is an atomic UPDATE ... WHERE status='valid', so two simultaneous scans admit once.
  T4  Beliefs: scans:<code> counts every scan of a code; 3 or more raises a suspicious_scan INFORM.
"""

from .base import Agent



class TicketAgent(Agent):
    name = "TicketAgent"

    