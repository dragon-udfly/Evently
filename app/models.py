from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .config import now
from .database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(20), default="attendee")  # admin | staff | attendee
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Venue(Base):
    __tablename__ = "venues"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    location: Mapped[str] = mapped_column(String(200))
    capacity: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str] = mapped_column(String(500), default="")
    hourly_rate: Mapped[float] = mapped_column(Float, default=0)
    open_for_hire: Mapped[bool] = mapped_column(Boolean, default=False)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"))
    start: Mapped[datetime] = mapped_column(DateTime)
    end: Mapped[datetime] = mapped_column(DateTime)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | published | cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    venue: Mapped[Venue] = relationship()
    categories: Mapped[list["TicketCategory"]] = relationship(
        back_populates="event", cascade="all, delete-orphan", order_by="TicketCategory.id")


class TicketCategory(Base):
    __tablename__ = "ticket_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    name: Mapped[str] = mapped_column(String(60))
    price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer)
    sold: Mapped[int] = mapped_column(Integer, default=0)  # sold + held seats
    event: Mapped[Event] = relationship(back_populates="categories")

    @property
    def left(self) -> int:
        return self.quantity - self.sold


