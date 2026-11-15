import uuid
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Performative = Literal["REQUEST", "AGREE", "REFUSE", "PROPOSE", "INFORM", "FAILURE"]


def new_id() -> str:
    return uuid.uuid4().hex[:16]


class Message(BaseModel):
    id: str = Field(default_factory=new_id)
    conversation_id: str = Field(default_factory=new_id)
    sender: str
    receiver: str  # agent name, or "*" for a broadcast INFORM
    performative: Performative
    content: dict[str, Any] = {}
    in_reply_to: Optional[str] = None

    @classmethod
    def make(cls, sender: str, receiver: str, performative: str,
             conversation_id: str | None = None, in_reply_to: str | None = None, **content) -> "Message":
        return cls(sender=sender, receiver=receiver, performative=performative,
                   conversation_id=conversation_id or new_id(), in_reply_to=in_reply_to, content=content)
