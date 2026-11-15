from .bus import MessageBus

class Agent:
    """Base agent: dispatches by content['action'] (REQUEST) or content['topic'] (INFORM)
    to a method called h_<name>, and owns persistent beliefs stored in agent_state."""
    name = "Agent"

    def __init__(self, bus: MessageBus):
        self.bus = bus

    