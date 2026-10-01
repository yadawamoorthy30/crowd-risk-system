from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, Numeric, String, func,
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
    area_sq_m = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    camera = relationship("Camera", back_populates="zones")