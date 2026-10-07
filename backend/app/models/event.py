import enum

from sqlalchemy import (
    Column, DateTime, Enum, ForeignKey, Integer, String, Text, func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class EventStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    event_type = Column(String(50), nullable=False, server_default="GENERAL")
    venue = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(Enum(EventStatus), nullable=False, server_default="PLANNED")
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    cameras = relationship(
        "Camera", back_populates="event", cascade="all, delete-orphan"
    )