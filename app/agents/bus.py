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

   