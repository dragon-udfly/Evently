import json
from sqlalchemy import Integer, String, cast, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..models import AgentState
from .bus import MessageBus
from .messages import Message


class Agent:
    """Base agent: dispatches by content['action'] (REQUEST) or content['topic'] (INFORM)
    to a method called h_<name>, and owns persistent beliefs stored in agent_state."""
    name = "Agent"

    def __init__(self, bus: MessageBus):
        self.bus = bus

    # ---- messaging ----
    def tell(self, db: Session, receiver: str, performative: str, conv: str, **content) -> Message | None:
        return self.bus.send(db, Message.make(self.name, receiver, performative, conv, **content))

    def broadcast(self, db: Session, conv: str, topic: str, **content):
        self.tell(db, "*", "INFORM", conv, topic=topic, **content)

    def reply(self, msg: Message, performative: str, **content) -> Message:
        return Message.make(self.name, msg.sender, performative, msg.conversation_id, msg.id, **content)

    def receive(self, db: Session, msg: Message) -> Message | None:
        key = msg.content.get("action") or msg.content.get("topic")
        handler = getattr(self, f"h_{key}", None)
        if handler is None:
            if msg.performative == "REQUEST":
                return self.reply(msg, "REFUSE", reason=f"{self.name} does not understand '{key}'")
            return None
        return handler(db, msg)

    # ---- beliefs (persistent state) ----
    def belief(self, db: Session, key: str, default=None):
        row = db.get(AgentState, (self.name, key))
        return json.loads(row.value) if row else default

    def set_belief(self, db: Session, key: str, value):
        row = db.get(AgentState, (self.name, key))
        if row is None:
            db.add(AgentState(agent=self.name, key=key, value=json.dumps(value, default=str)))
        else:
            row.value = json.dumps(value, default=str)

    def bump(self, db: Session, key: str, by: int = 1) -> int:
        """Atomic counter belief (safe when two requests increment together)."""
        stmt = (update(AgentState).where(AgentState.agent == self.name, AgentState.key == key)
                .values(value=cast(cast(AgentState.value, Integer) + by, String))
                .execution_options(synchronize_session=False))
        if db.execute(stmt).rowcount == 0:
            try:
                with db.begin_nested():
                    db.add(AgentState(agent=self.name, key=key, value=str(by)))
                    db.flush()
            except IntegrityError:  # another request created it first
                db.execute(stmt)
        return int(db.scalar(select(AgentState.value).where(AgentState.agent == self.name, AgentState.key == key)))
