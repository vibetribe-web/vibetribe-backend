import enum
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EventType(str, enum.Enum):
    hackathon = "hackathon"
    event = "event"


class EventMode(str, enum.Enum):
    online = "online"
    offline = "offline"
    hybrid = "hybrid"


class EventStatus(str, enum.Enum):
    upcoming = "upcoming"
    ongoing = "ongoing"
    finished = "finished"


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_club_id", "club_id"),
        Index("ix_events_created_by", "created_by"),
        Index("ix_events_start_date", "start_date"),
        CheckConstraint("end_date >= start_date", name="ck_events_end_date_after_start_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="event_type"),
        nullable=False,
    )
    mode: Mapped[EventMode] = mapped_column(
        Enum(EventMode, name="event_mode"),
        nullable=False,
    )
    venue: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registration_link: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    club = relationship("Club", back_populates="events")
    creator = relationship("User", back_populates="events_created")
    team_messages = relationship("TeamMessage", back_populates="event", passive_deletes=True)
    teams = relationship("Team", back_populates="event", passive_deletes=True)
    interests = relationship(
        "EventInterest",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def event_status(self) -> EventStatus:
        now = datetime.now(timezone.utc)
        start_date = _as_aware_utc(self.start_date)
        end_date = _as_aware_utc(self.end_date)
        if now < start_date:
            return EventStatus.upcoming
        if now <= end_date:
            return EventStatus.ongoing
        return EventStatus.finished
