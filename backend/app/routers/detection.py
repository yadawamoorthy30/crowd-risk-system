from dataclasses import asdict
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.camera import Camera, CameraStatus, SourceType
from app.models.detection_run import DetectionRun
from app.models.metric_snapshot import MetricSnapshot
from app.schemas.detection import (
    BBox,
    CountPoint,
    DetectionHistoryResponse,
    DetectionResultsResponse,
    DetectionStartRequest,
    DetectionStatusResponse,
    DetectionStopRequest,
    FlowOut,
    MetricsOut,
    Point,
    TrackOut,
)
from app.services.video_source import check_source
from app.services.vision.config import VisionConfig
from app.services.vision.manager import SessionAlreadyRunning, detection_manager
from app.services.vision.metrics import MonitorArea
from app.models.tripwire import Tripwire
from app.services.vision.flow import TripwireLine

router = APIRouter(prefix="/api/detection", tags=["Detection"])


def _to_status(session) -> DetectionStatusResponse:
    p = session.processor
    return DetectionStatusResponse(
        camera_id=session.camera_id,
        state=session.state,
        source=session.source,
        started_at=session.started_at,
        frames_read=p.frames_read,
        frames_processed=p.frames_processed,
        frames_skipped=p.frames_skipped,
        fps=round(p.fps, 1),
        target_fps=p.config.target_fps,
        conf=p.config.conf,
        frame_width=p.frame_width or None,
        frame_height=p.frame_height or None,
        unique_track_ids=p.tracks.unique_ids,
        tracks_in_memory=p.tracks.tracks_in_memory,
        run_id=session.run_id,
        snapshots_saved=session.snapshots_saved,
        db_errors=session.db_errors,
        error=session.error,
        flow=_flow_out(p),
    )


def _require_camera(db: Session, camera_id: int) -> None:
    if db.get(Camera, camera_id) is None:
        raise HTTPException(status_code=404, detail=f"Camera with id {camera_id} not found")

def _flow_out(processor) -> FlowOut:
    fm = processor.latest_flow
    if fm is None:   # no frame has been processed yet
        return FlowOut(
            tripwire_configured=processor.flow is not None,
            message="Waiting for first frame" if processor.flow is not None
            else "Tripwire not configured",
        )
    return FlowOut(**asdict(fm))

def _load_tripwire(db: Session, camera_id: int) -> Optional[TripwireLine]:
    row = db.query(Tripwire).filter(Tripwire.camera_id == camera_id).first()
    return TripwireLine.from_model(row) if row is not None else None


def _build_monitor(camera: Camera) -> MonitorArea:
    zone = camera.active_zone
    if zone is not None:
        return MonitorArea(
            mode="zone",
            area_sqm=float(zone.area_sqm),
            zone_id=zone.id,
            zone_name=zone.name,
            polygon=zone.polygon,
        )
    return MonitorArea(
        mode="full_frame",
        area_sqm=float(camera.area_sqm) if camera.area_sqm is not None else None,
    )


@router.post("/start", response_model=DetectionStatusResponse,
             status_code=status.HTTP_202_ACCEPTED)
def start_detection(payload: DetectionStartRequest, db: Session = Depends(get_db)):
    camera = db.get(Camera, payload.camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail=f"Camera with id {payload.camera_id} not found")
    if camera.status == CameraStatus.DISABLED:
        raise HTTPException(status_code=400, detail="Camera is not active")
    if camera.source_type in (SourceType.RTSP, SourceType.HTTP):
        raise HTTPException(status_code=400, detail="RTSP cameras are not supported yet")

    check = check_source(camera)
    if check["reachable"] is False:
        raise HTTPException(status_code=400, detail=f"Source not usable: {check['message']}")

    config = VisionConfig(
        conf=payload.conf if payload.conf is not None else camera.min_confidence,
        imgsz=payload.imgsz,
        track_buffer=payload.track_buffer,
        target_fps=camera.processing_fps,
        realtime=payload.realtime or camera.source_type == SourceType.USB,
        smoothing_seconds=payload.smoothing_seconds,
        initial_count=payload.initial_count,
        flow_window_sec=payload.flow_window_sec,
        growth_window_sec=payload.growth_window_sec,
    )
    try:
        session = detection_manager.start(
            camera.id, camera.source_path, config, _build_monitor(camera),
            tripwire=_load_tripwire(db, camera.id),
        )
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
            frame_width=result.frame_width,
            frame_height=result.frame_height,
            tracks=[
                TrackOut(
                    track_id=p.track_id,
                    confidence=p.confidence,
                    bbox=BBox(x=p.x, y=p.y, width=p.width, height=p.height),
                    foot_point=Point(x=p.foot_x, y=p.foot_y),
                    counted=p.counted,
                )
                for p in result.people
            ],
            metrics=MetricsOut(**asdict(result.metrics)) if result.metrics else None,
            flow=_flow_out(session.processor),
        )

    # 2) Otherwise: the last aggregated sample saved in MySQL.
    #    Per-track data is never stored, so tracks is empty here.
    row = (
        db.query(MetricSnapshot)
        .filter(MetricSnapshot.camera_id == camera_id)
        .order_by(MetricSnapshot.id.desc())
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No detection results stored for camera {camera_id}",
        )

    return DetectionResultsResponse(
        camera_id=camera_id,
        source="database",
        timestamp=row.ts,
        people_detected=row.person_count,
        metrics=MetricsOut(people_count=row.person_count, density=row.density),
        tracks=[],
    )


@router.get("/history/{camera_id}", response_model=DetectionHistoryResponse)
def detection_history(
    camera_id: int,
    limit: int = Query(60, ge=1, le=500),
    db: Session = Depends(get_db),
):
    _require_camera(db, camera_id)

    rows = (
        db.query(MetricSnapshot)
        .filter(MetricSnapshot.camera_id == camera_id)
        .order_by(MetricSnapshot.id.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()  # oldest first, which is the natural order for a chart

    return DetectionHistoryResponse(
        camera_id=camera_id,
        count=len(rows),
        points=[
            CountPoint(ts=r.ts, person_count=r.person_count, density=r.density)
            for r in rows
        ],
    )