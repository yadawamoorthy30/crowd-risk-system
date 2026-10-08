from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func

from app.database import Base


class DetectionRun(Base):
    __tablename__ = "detection_runs"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(
        Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True
    )
    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="running")
    conf = Column(Float, nullable=False)
    imgsz = Column(Integer, nullable=False)
    tracker = Column(String(50), nullable=False)
    frames_processed = Column(Integer, nullable=False, default=0)
    error_message = Column(String(255), nullable=True)