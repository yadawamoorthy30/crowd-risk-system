from datetime import datetime
from typing import Optional

from app.database import SessionLocal
from app.models.detection_run import DetectionRun
from app.models.metric_snapshot import MetricSnapshot
from app.services.vision.config import VisionConfig
from app.services.vision.results import FrameResult


def create_run(camera_id: int, config: VisionConfig) -> int:
    db = SessionLocal()
    try:
        run = DetectionRun(
            camera_id=camera_id,
            status="running",
            conf=config.conf,
            imgsz=config.imgsz,
            tracker=config.tracker,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run.id
    finally:
        db.close()


def save_metrics(camera_id: int, result: FrameResult) -> None:
    """Store ONLY aggregated metrics. Per-track data never reaches the database."""
    if result.metrics is None:
        return
    db = SessionLocal()
    try:
        db.add(MetricSnapshot(
            camera_id=camera_id,
            ts=result.timestamp,
            person_count=result.metrics.people_count,
            density=result.metrics.density,
        ))
        db.commit()
    finally:
        db.close()


def finish_run(run_id: int, status: str, frames_processed: int,
               error: Optional[str] = None) -> None:
    db = SessionLocal()
    try:
        run = db.get(DetectionRun, run_id)
        if run is not None:
            run.status = status
            run.ended_at = datetime.now()
            run.frames_processed = frames_processed
            run.error_message = error[:255] if error else None
            db.commit()
    finally:
        db.close()


def close_orphaned_runs() -> int:
    """Called at startup: any run still 'running' belongs to a dead process."""
    db = SessionLocal()
    try:
        orphans = db.query(DetectionRun).filter(DetectionRun.status == "running").all()
        for run in orphans:
            run.status = "interrupted"
            run.ended_at = datetime.now()
        db.commit()
        return len(orphans)
    except Exception as error:
        db.rollback()
        print(f"Could not close orphaned runs: {error}")
        return 0
    finally:
        db.close()