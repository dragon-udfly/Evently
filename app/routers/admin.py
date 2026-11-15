import json

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..agents.registry import request as ask
from ..agents.scheduler import run_sweep
from ..database import get_db
from ..models import (AgentMessage, AgentState, Booking, Event, HireRequest, Notification, Ticket,
                      TicketCategory, Venue)
from ..schemas import EVENT_CATEGORIES, CategoryIn, EventIn, VenueIn, first_error
from ..security import csrf_protect, flash, require_role
from ..web import go, render

router = APIRouter(prefix="/admin")
admin_only = require_role("admin")
CSRF = [Depends(csrf_protect)]
