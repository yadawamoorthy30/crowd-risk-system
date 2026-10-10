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
    # Flow values added in Phase 3 (SRS 8.1.7). All nullable: old rows keep NULL,
    # and a camera without a tripwire has no IN/OUT/occupancy values.
    in_count = Column(Integer, nullable=True)               # IN in the rolling window
    out_count = Column(Integer, nullable=True)              # OUT in the rolling window
    net_flow = Column(Integer, nullable=True)               # F(t) = in_count - out_count
    cumulative_occupancy = Column(Integer, nullable=True)   # initial + sum(IN) - sum(OUT)
    growth_rate = Column(Float, nullable=True)              # R(t), people per minute