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


