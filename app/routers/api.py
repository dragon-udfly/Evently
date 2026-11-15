import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..agents.messages import Message
from ..agents.registry import AGENT_NAMES, bus
from ..config import settings
from ..database import get_db
from ..schemas import AgentMessageIn

router = APIRouter(prefix="/api")
