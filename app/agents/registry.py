from sqlalchemy.orm import Session
from .booking_agent import BookingAgent
from .bus import MessageBus
from .messages import Message
from .notification_agent import NotificationAgent
from .ticket_agent import TicketAgent
from .venue_agent import VenueAgent
from .waitlist_agent import WaitlistAgent


def build_bus() -> MessageBus:
    bus = MessageBus()
    bus.register(VenueAgent(bus))
    bus.register(BookingAgent(bus))
    bus.register(TicketAgent(bus))
    bus.register(WaitlistAgent(bus))
    bus.register(NotificationAgent(bus), listens=True)
    return bus


bus = build_bus()
AGENT_NAMES = list(bus.agents)


def request(db: Session, sender: str, receiver: str, action: str, **content) -> Message:
    """A user action becomes a REQUEST message with a fresh conversation id; returns the reply."""
    return bus.send(db, Message.make(sender, receiver, "REQUEST", None, action=action, **content))
