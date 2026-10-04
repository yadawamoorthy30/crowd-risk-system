from datetime import datetime
from typing import Optional

from app.database import SessionLocal
from app.models.detection_run import DetectionRun
from app.models.detection_snapshot import DetectionSnapshot
from app.models.track_observation import TrackObservation
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


def save_snapshot(run_id: int, result: FrameResult) -> None:
    db = SessionLocal()
    try:
        snapshot = DetectionSnapshot(
            run_id=run_id,
            frame_number=result.frame_number,
            captured_at=result.timestamp,
            people_count=result.people_detected,
        )
        snapshot.observations = [
            TrackObservation(
                track_id=p.track_id,
                confidence=p.confidence,
                x=p.x,
                y=p.y,
                width=p.width,
                height=p.height,
            )
            for p in result.people
        ]
        db.add(snapshot)
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