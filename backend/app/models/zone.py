from sqlalchemy import (
    JSON, Column, DateTime, ForeignKey, Integer, Numeric, String, func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(
        Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(100), nullable=False)
    # normalised points [[x, y], ...], each value between 0 and 1
    polygon = Column(JSON, nullable=False)
    area_sqm = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    camera = relationship(
        "Camera", back_populates="zones", foreign_keys=[camera_id]
    )

    @property
    def is_active(self) -> bool:
        return self.camera is not None and self.camera.active_zone_id == self.id