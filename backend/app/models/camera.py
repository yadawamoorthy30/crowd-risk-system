import enum

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, func, text,
)
from sqlalchemy.orm import relationship

from app.database import Base


class SourceType(str, enum.Enum):
    video_file = "video_file"
    webcam = "webcam"
    rtsp = "rtsp"


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(
        Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(100), nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    source_path = Column(String(500), nullable=False)
    location_description = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("1"))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    event = relationship("Event", back_populates="cameras")
    zones = relationship(
        "Zone", back_populates="camera", cascade="all, delete-orphan"
    )