"""Pydantic validation for every form / JSON input."""
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

EVENT_CATEGORIES = ["Concert", "Workshop", "Seminar", "Conference", "Other"]


def first_error(exc: ValidationError) -> str:
    e = exc.errors()[0]
    field = ".".join(str(p) for p in e["loc"]) or "input"
    return f"{field}: {e['msg']}"


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(max_length=200)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
            raise ValueError("invalid email address")
        return v


class VenueIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    location: str = Field(min_length=2, max_length=200)
    capacity: int = Field(gt=0, le=100000)
    description: str = ""
    image_url: str = ""
    hourly_rate: float = Field(ge=0)
    open_for_hire: bool = False


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    price: float = Field(ge=0)
    quantity: int = Field(gt=0)


class EventIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    category: Literal["Concert", "Workshop", "Seminar", "Conference", "Other"]
    venue_id: int
    start: datetime
    end: datetime
    description: str = ""
    categories: list[CategoryIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _times(self):
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self

class HireIn(BaseModel):
    venue_id: int
    start: datetime
    end: datetime
    guests: int = Field(gt=0)
    purpose: str = Field(min_length=3, max_length=300)


class ScanIn(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    event_id: int

