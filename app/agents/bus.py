"""In-process message bus. Agents never call each other: they send Messages through here.

Every message (requests, replies, broadcasts) is written to agent_messages BEFORE delivery,
so one user action can be traced across agents by its conversation_id.
"""
import json
from sqlalchemy.orm import Session
from app.agents.base import Agent
from ..models import AgentMessage
from .messages import Message


class MessageBus:
    def __init__(self):
        self.agents: dict[str, "Agent"] = {}  # noqa: F821
        self.listeners: list[str] = []         # agents that receive broadcasts

    def register(self, agent, listens: bool = False):
        self.agents[agent.name] = agent
        if listens:
            self.listeners.append(agent.name)

    def _log(self, db: Session, msg: Message):
        db.add(AgentMessage(
            message_id=msg.id, conversation_id=msg.conversation_id, sender=msg.sender,
            receiver=msg.receiver, performative=msg.performative,
            content=json.dumps(msg.content, default=str)))

    def send(self, db: Session, msg: Message) -> Message | None:
        self._log(db, msg)
        if msg.receiver == "*":  # broadcast: reactive listeners only
            for name in self.listeners:
                if name != msg.sender:
                    self._deliver(db, name, msg)
            return None
        return self._deliver(db, msg.receiver, msg)

    def _deliver(self, db: Session, name: str, msg: Message) -> Message | None:
        agent = self.agents.get(name)
        if agent is None:
            reply = Message.make("Bus", msg.sender, "FAILURE", msg.conversation_id, msg.id,
                                 reason=f"unknown receiver '{name}'")
        else:
            try:
                reply = agent.receive(db, msg)
            except Exception as exc:  
                db.rollback()
                reply = Message.make(name, msg.sender, "FAILURE", msg.conversation_id, msg.id,
                                     reason=f"{type(exc).__name__}: {exc}")
        if reply is not None:
            self._log(db, reply)
        return reply
