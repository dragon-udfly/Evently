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
