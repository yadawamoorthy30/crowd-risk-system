from pathlib import Path

from app.models.heatmap_snapshot import HeatmapMode, HeatmapSnapshot
from app.services.vision.heatmap_snapshot import (
    build_image_path, heatmap_fields, render_snapshot_png,
)

from datetime import datetime
from typing import Optional

from app.database import SessionLocal
from app.models.detection_run import DetectionRun
from app.models.metric_snapshot import MetricSnapshot
from app.services.vision.config import VisionConfig
from app.services.vision.results import FrameResult
from app.services.vision.snapshot_fields import metric_fields


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
    fields = metric_fields(result)
    if fields is None:
        return
    db = SessionLocal()
    try:
        db.add(MetricSnapshot(camera_id=camera_id, **fields))
        db.commit()
    finally:
        db.close()

STORAGE_ROOT = Path(__file__).resolve().parents[3] / "storage"   # backend/storage


def save_heatmap(camera_id: int, calc, mode: str, frame_w: int, frame_h: int) -> None:
    """Save one heatmap snapshot: a database row plus a heatmap-only PNG.

    Only grid values and a picture drawn from them are stored, never a camera frame.
    """
    ts = datetime.now()
    fields = heatmap_fields(calc, mode, ts)
    relative = build_image_path(camera_id, ts, mode)
    target = STORAGE_ROOT / relative
    png = render_snapshot_png(calc, mode, frame_w, frame_h)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(png)

    db = SessionLocal()
    try:
        fields["mode"] = HeatmapMode(fields["mode"])
        db.add(HeatmapSnapshot(camera_id=camera_id, image_path=relative, **fields))
        db.commit()
    except Exception:
        target.unlink(missing_ok=True)      # do not leave a file without a row
        raise
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