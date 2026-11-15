from fastapi import APIRouter, Depends, Form, Request
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import RegisterIn, first_error
from ..security import csrf_protect, flash, get_current_user, hash_password, verify_password
from ..web import go, render

router = APIRouter()


def _start_session(request: Request, user: User):
    request.session.clear()  # new session id on login (prevents fixation)
    request.session["user_id"] = user.id


@router.get("/register")
def register_page(request: Request, user=Depends(get_current_user)):
    return render(request, "register.html", user)


@router.post("/register", dependencies=[Depends(csrf_protect)])
def register(request: Request, name: str = Form(""), email: str = Form(""), password: str = Form(""),
             db: Session = Depends(get_db)):
    try:
        data = RegisterIn(name=name, email=email, password=password)
    except ValidationError as e:
        flash(request, first_error(e), "danger")
        return go("/register")
    if db.scalar(select(User).where(User.email == data.email)):
        flash(request, "That email is already registered", "danger")
        return go("/register")
    user = User(name=data.name, email=data.email, password_hash=hash_password(data.password), role="attendee")
    db.add(user)
    db.commit()
    _start_session(request, user)
    flash(request, "Welcome to Evently!", "success")
    return go("/")


@router.get("/login")
def login_page(request: Request, user=Depends(get_current_user)):
    return render(request, "login.html", user)


@router.post("/login", dependencies=[Depends(csrf_protect)])
def login(request: Request, email: str = Form(""), password: str = Form(""), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not verify_password(password, user.password_hash):
        flash(request, "Wrong email or password", "danger")
        return go("/login")
    _start_session(request, user)
    return go({"admin": "/admin", "staff": "/staff/scanner"}.get(user.role, "/"))


@router.post("/logout", dependencies=[Depends(csrf_protect)])
def logout(request: Request):
    request.session.clear()
    return go("/")
