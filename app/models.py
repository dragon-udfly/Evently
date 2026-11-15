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


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("ticket_categories.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="confirmed")  # confirmed | cancelled | failed
    total: Mapped[float] = mapped_column(Float, default=0)
    refund_amount: Mapped[float] = mapped_column(Float, default=0)
    payment_ref: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    event: Mapped[Event] = relationship()
    category: Mapped[TicketCategory] = relationship()
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="booking")


class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="valid")  # valid | used | cancelled
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    booking: Mapped[Booking] = relationship(back_populates="tickets")


class Waitlist(Base):
    __tablename__ = "waitlist"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("ticket_categories.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="waiting")  # waiting | held | claimed | expired | left
    hold_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    event: Mapped[Event] = relationship()
    category: Mapped[TicketCategory] = relationship()


class HireRequest(Base):
    __tablename__ = "hire_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"))
    start: Mapped[datetime] = mapped_column(DateTime)
    end: Mapped[datetime] = mapped_column(DateTime)
    purpose: Mapped[str] = mapped_column(String(300))
    guests: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))  # confirmed | pending | rejected
    price: Mapped[float] = mapped_column(Float, default=0)
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    venue: Mapped[Venue] = relationship()
    user: Mapped[User] = relationship()


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    audience: Mapped[str] = mapped_column(String(20), default="user")  # user | admin
    message: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


