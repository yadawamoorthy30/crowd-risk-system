from sqlalchemy import Column, Float, ForeignKey, Index, Integer
from sqlalchemy.dialects.mysql import DATETIME

from app.database import Base


class MetricSnapshot(Base):
    """Aggregated metrics only (SRS 8.1.7): no track IDs, no per-person data."""
    __tablename__ = "metric_snapshots"
    __table_args__ = (Index("ix_metric_snapshots_camera_ts", "camera_id", "ts"),)

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(
        Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
    )
    ts = Column(DATETIME(fsp=3), nullable=False)
    person_count = Column(Integer, nullable=False)
    density = Column(Float, nullable=True)