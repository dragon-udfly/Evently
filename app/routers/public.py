import io
from datetime import datetime

import segno
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..agents.registry import request as ask
from ..config import now
from ..database import get_db
from ..models import Booking, Event, Notification, Ticket, TicketCategory, Venue, Waitlist
from ..policy import REFUND_POLICY, refund_pct
from ..schemas import EVENT_CATEGORIES
from ..security import csrf_protect, flash, get_current_user, login_required
from ..web import go, render

router = APIRouter()

