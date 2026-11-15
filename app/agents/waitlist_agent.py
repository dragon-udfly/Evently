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
from .base import Agent


class WaitlistAgent(Agent):
    name = "WaitlistAgent"

    