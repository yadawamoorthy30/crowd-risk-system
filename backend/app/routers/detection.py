from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.camera import Camera, SourceType
from app.models.detection_run import DetectionRun
from app.models.detection_snapshot import DetectionSnapshot
from app.schemas.detection import (
    BBox,
    CountPoint,
    DetectionHistoryResponse,
    DetectionResultsResponse,
    DetectionStartRequest,
    DetectionStatusResponse,
    DetectionStopRequest,
    TrackOut,
)
from app.services.video_source import check_source
from app.services.vision.config import VisionConfig
from app.services.vision.manager import SessionAlreadyRunning, detection_manager

router = APIRouter(prefix="/api/detection", tags=["Detection"])


def _to_status(session) -> DetectionStatusResponse:
    return DetectionStatusResponse(
        camera_id=session.camera_id,
        state=session.state,
        source=session.source,
        started_at=session.started_at,
        frames_processed=session.processor.frames_processed,
        fps=round(session.processor.fps, 1),
        unique_track_ids=session.processor.tracks.unique_ids,
        run_id=session.run_id,
        snapshots_saved=session.snapshots_saved,
        db_errors=session.db_errors,
        error=session.error,
    )


def _require_camera(db: Session, camera_id: int) -> None:
    if db.get(Camera, camera_id) is None:
        raise HTTPException(status_code=404, detail=f"Camera with id {camera_id} not found")


@router.post("/start", response_model=DetectionStatusResponse,
             status_code=status.HTTP_202_ACCEPTED)
def start_detection(payload: DetectionStartRequest, db: Session = Depends(get_db)):
    camera = db.get(Camera, payload.camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail=f"Camera with id {payload.camera_id} not found")
    if not camera.is_active:
        raise HTTPException(status_code=400, detail="Camera is not active")
    if camera.source_type == SourceType.rtsp:
        raise HTTPException(status_code=400, detail="RTSP cameras are not supported yet")

    check = check_source(camera)
    if check["reachable"] is False:
        raise HTTPException(status_code=400, detail=f"Source not usable: {check['message']}")

    config = VisionConfig(conf=payload.conf, imgsz=payload.imgsz)
    try:
        session = detection_manager.start(camera.id, camera.source_path, config)
    except SessionAlreadyRunning as error:
        raise HTTPException(status_code=409, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not start detection: {error}")

    return _to_status(session)


@router.post("/stop", response_model=DetectionStatusResponse)
def stop_detection(payload: DetectionStopRequest):
    session = detection_manager.stop(payload.camera_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"No detection session found for camera {payload.camera_id}",
        )
    return _to_status(session)


@router.get("/status", response_model=List[DetectionStatusResponse])
def detection_status(camera_id: Optional[int] = None):
    return [_to_status(session) for session in detection_manager.sessions(camera_id)]


@router.get("/results/{camera_id}", response_model=DetectionResultsResponse)
def latest_results(camera_id: int, db: Session = Depends(get_db)):
    _require_camera(db, camera_id)

    # 1) Camera is running: answer from memory (newest frame)
    session = detection_manager.get(camera_id)
    if session is not None and session.state == "running":
        result = session.latest
        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Detection just started; no results yet, try again in a moment",
            )
        return DetectionResultsResponse(
            camera_id=camera_id,
            run_id=session.run_id,
            source="live",
            frame_number=result.frame_number,
            timestamp=result.timestamp,
            people_detected=result.people_detected,
            tracks=[
                TrackOut(
                    track_id=p.track_id,
                    confidence=p.confidence,
                    bbox=BBox(x=p.x, y=p.y, width=p.width, height=p.height),
                )
                for p in result.people
            ],
        )

    # 2) Otherwise: the last snapshot saved in MySQL
    snapshot = (
        db.query(DetectionSnapshot)
        .join(DetectionRun, DetectionSnapshot.run_id == DetectionRun.id)
        .filter(DetectionRun.camera_id == camera_id)
        .order_by(DetectionSnapshot.id.desc())
        .first()
    )
    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail=f"No detection results stored for camera {camera_id}",
        )

    return DetectionResultsResponse(
        camera_id=camera_id,
        run_id=snapshot.run_id,
        source="database",
        frame_number=snapshot.frame_number,
        timestamp=snapshot.captured_at,
        people_detected=snapshot.people_count,
        tracks=[
            TrackOut(
                track_id=o.track_id,
                confidence=o.confidence,
                bbox=BBox(x=o.x, y=o.y, width=o.width, height=o.height),
            )
            for o in snapshot.observations
        ],
    )


@router.get("/history/{camera_id}", response_model=DetectionHistoryResponse)
def detection_history(
    camera_id: int,
    limit: int = Query(60, ge=1, le=500),
    db: Session = Depends(get_db),
):
    _require_camera(db, camera_id)

    rows = (
        db.query(DetectionSnapshot)
        .join(DetectionRun, DetectionSnapshot.run_id == DetectionRun.id)
        .filter(DetectionRun.camera_id == camera_id)
        .order_by(DetectionSnapshot.id.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()  # oldest first, which is the natural order for a chart

    return DetectionHistoryResponse(
        camera_id=camera_id,
        count=len(rows),
        points=[
            CountPoint(
                run_id=r.run_id,
                frame_number=r.frame_number,
                captured_at=r.captured_at,
                people_count=r.people_count,
            )
            for r in rows
        ],
    )