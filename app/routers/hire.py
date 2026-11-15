from fastapi import APIRouter, Depends, Form, Request
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents.registry import request as ask
from ..database import get_db
from ..models import HireRequest, Venue
from ..schemas import HireIn, first_error
from ..security import csrf_protect, flash, login_required
from ..web import go, render

router = APIRouter()


def _page(request, user, db, result=None, form=None):
    venues = db.scalars(select(Venue).where(Venue.open_for_hire.is_(True)).order_by(Venue.name)).all()
    mine = db.scalars(select(HireRequest).where(HireRequest.user_id == user.id).order_by(HireRequest.id.desc())).all()
    return render(request, "hire.html", user, venues=venues, mine=mine, result=result, form=form or {})
