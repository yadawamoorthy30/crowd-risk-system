import enum

from sqlalchemy import JSON, Column, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.mysql import DATETIME

from app.database import Base


class HeatmapMode(str, enum.Enum):
    INSTANT = "INSTANT"
    WINDOW = "WINDOW"


class HeatmapSnapshot(Base):
    """Saved heatmap (SRS 8.1.8). Aggregated cell values only, plus a heatmap-only
    image drawn on a black background: no camera frame, so nobody is identifiable."""
    __tablename__ = "heatmap_snapshots"
    __table_args__ = (Index("ix_heatmap_snapshots_camera_ts", "camera_id", "ts"),)

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(
        Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
    )
    ts = Column(DATETIME(fsp=3), nullable=False)
    mode = Column(Enum(HeatmapMode), nullable=False)
    window_sec = Column(Integer, nullable=True)       # NULL for INSTANT
    grid_cols = Column(Integer, nullable=False)
    grid_rows = Column(Integer, nullable=False)
    grid_data = Column(JSON, nullable=False)          # rows x cols of cell values
    image_path = Column(String(255), nullable=True)   # relative to backend/storage
    # alert_id is added in Phase 4, when alerts exist