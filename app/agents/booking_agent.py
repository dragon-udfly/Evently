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
from .base import Agent

class BookingAgent(Agent):
    name = "BookingAgent"

    