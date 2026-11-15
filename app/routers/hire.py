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


@router.get("/hire")
def hire_page(request: Request, user=Depends(login_required), db: Session = Depends(get_db)):
    return _page(request, user, db)


@router.post("/hire", dependencies=[Depends(csrf_protect)])
def hire_submit(request: Request, venue_id: str = Form(""), start: str = Form(""), end: str = Form(""),
                guests: str = Form(""), purpose: str = Form(""), user=Depends(login_required),
                db: Session = Depends(get_db)):
    try:
        data = HireIn(venue_id=venue_id, start=start, end=end, guests=guests, purpose=purpose)
    except ValidationError as e:
        flash(request, first_error(e), "danger")
        return go("/hire")
    reply = ask(db, f"user:{user.id}", "VenueAgent", "hire_request", user_id=user.id, venue_id=data.venue_id,
                start=data.start.isoformat(), end=data.end.isoformat(), guests=data.guests, purpose=data.purpose)
    db.commit()
    result = {"performative": reply.performative, **reply.content}
    return _page(request, user, db, result=result, form=data.model_dump(mode="json"))
