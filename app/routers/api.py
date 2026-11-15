import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..agents.messages import Message
from ..agents.registry import AGENT_NAMES, bus
from ..config import settings
from ..database import get_db
from ..schemas import AgentMessageIn

router = APIRouter(prefix="/api")


@router.post("/agents/{name}/inbox")
def inbox(name: str, body: AgentMessageIn, x_agent_key: str = Header(""), db: Session = Depends(get_db)):
    if not settings.agent_api_key or not hmac.compare_digest(x_agent_key, settings.agent_api_key):
        raise HTTPException(403, "Invalid or missing X-Agent-Key")
    if name not in AGENT_NAMES:
        raise HTTPException(404, f"Unknown agent. Available: {AGENT_NAMES}")
    msg = Message.make(f"http:{body.sender}", name, body.performative, body.conversation_id, **body.content)
    reply = bus.send(db, msg)
    db.commit()
    return reply.model_dump() if reply else {"status": "delivered", "conversation_id": msg.conversation_id}


@router.get("/healthz")
def health():
    return {"status": "ok"}
