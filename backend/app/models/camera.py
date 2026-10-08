import enum

from sqlalchemy import (
    Column, DateTime, Enum, Float, ForeignKey, Integer, Numeric, String, Text, func, text,
)
from sqlalchemy.orm import relationship

from app.database import Base


class SourceType(str, enum.Enum):
    RTSP = "RTSP"
    HTTP = "HTTP"
    USB = "USB"
    FILE = "FILE"


class CameraStatus(str, enum.Enum):
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    DISCONNECTED = "DISCONNECTED"
    DISABLED = "DISABLED"


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

    # monitored area A (full-frame mode). A zone's own area overrides it.
    area_length_m = Column(Numeric(8, 2), nullable=True)
    area_width_m = Column(Numeric(8, 2), nullable=True)
    area_sqm = Column(Numeric(10, 2), nullable=True)

    min_confidence = Column(Float, nullable=False, server_default=text("0.40"))
    processing_fps = Column(Integer, nullable=False, server_default=text("10"))
    status = Column(
        Enum(CameraStatus), nullable=False, server_default="DISCONNECTED"
    )
    active_zone_id = Column(
        Integer, ForeignKey("zones.id", ondelete="SET NULL"), nullable=True
    )
    credentials_encrypted = Column(Text, nullable=True)  # Fernet token; never returned by the API
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    event = relationship("Event", back_populates="cameras")

    # All zones DEFINED for this camera (Zone.camera_id -> cameras.id)
    zones = relationship(
        "Zone",
        back_populates="camera",
        foreign_keys="Zone.camera_id",
        cascade="all, delete-orphan",
    )
    # The ONE zone currently selected (cameras.active_zone_id -> zones.id)
    active_zone = relationship(
        "Zone", foreign_keys=[active_zone_id], post_update=True
    )

    @property
    def has_credentials(self) -> bool:
        return self.credentials_encrypted is not None