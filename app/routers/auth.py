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


@router.get("/register")
def register_page(request: Request, user=Depends(get_current_user)):
    return render(request, "register.html", user)
