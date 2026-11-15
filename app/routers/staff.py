from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents.registry import request as ask
from ..config import now
from ..database import get_db
from ..models import Event
from ..schemas import ScanIn
from ..security import csrf_protect, require_role
from ..web import render

router = APIRouter()
staff_only = require_role("staff", "admin")


@router.get("/staff/scanner")
def scanner(request: Request, user=Depends(staff_only), db: Session = Depends(get_db)):
    events = db.scalars(select(Event).where(Event.status == "published", Event.end > now()).order_by(Event.start)).all()
    return render(request, "scanner.html", user, events=events)
