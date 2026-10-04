from sqlalchemy import Column, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.database import Base


class TrackObservation(Base):
    __tablename__ = "track_observations"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(
        Integer, ForeignKey("detection_snapshots.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    track_id = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)

    snapshot = relationship("DetectionSnapshot", back_populates="observations")