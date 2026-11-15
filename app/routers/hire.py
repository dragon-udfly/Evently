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


