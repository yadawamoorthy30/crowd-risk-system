from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import relationship

from app.database import Base


class DetectionSnapshot(Base):
    __tablename__ = "detection_snapshots"
    __table_args__ = (Index("ix_snapshots_run_captured", "run_id", "captured_at"),)

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(
        Integer, ForeignKey("detection_runs.id", ondelete="CASCADE"), nullable=False
    )
    frame_number = Column(Integer, nullable=False)
    captured_at = Column(DateTime, nullable=False)
    people_count = Column(Integer, nullable=False)

    run = relationship("DetectionRun", back_populates="snapshots")
    observations = relationship(
        "TrackObservation", back_populates="snapshot", cascade="all, delete-orphan"
    )