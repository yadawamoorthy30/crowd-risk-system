from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.camera import Camera
from app.models.event import Event
from app.models.zone import Zone
from app.schemas.camera import ActiveZoneUpdate, CameraAreaUpdate, CameraCreate, CameraResponse, SourceCheckResponse
from app.services.video_source import check_source

router = APIRouter(prefix="/api/cameras", tags=["Cameras"])


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
def create_camera(payload: CameraCreate, db: Session = Depends(get_db)):
    event = db.get(Event, payload.event_id)
    if event is None:
        raise HTTPException(
            status_code=404,
            detail=f"Event with id {payload.event_id} not found",
        )

    camera = Camera(**payload.model_dump())
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera


@router.get("", response_model=List[CameraResponse])
def list_cameras(event_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Camera)
    if event_id is not None:
        query = query.filter(Camera.event_id == event_id)
    return query.order_by(Camera.id).all()

@router.get("/{camera_id}/verify-source", response_model=SourceCheckResponse)
def verify_camera_source(camera_id: int, db: Session = Depends(get_db)):
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera with id {camera_id} not found",
        )
    return check_source(camera)

@router.put("/{camera_id}/area", response_model=CameraResponse)
def set_camera_area(
    camera_id: int, payload: CameraAreaUpdate, db: Session = Depends(get_db)
):
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera with id {camera_id} not found",
        )

    area = payload.computed_area()
    if area <= 0:
        raise HTTPException(
            status_code=422,
            detail="Area is too small: it rounds to 0.00 m²",
        )

    if payload.area_sqm is not None:
        camera.area_length_m = None
        camera.area_width_m = None
    else:
        camera.area_length_m = payload.area_length_m
        camera.area_width_m = payload.area_width_m
    camera.area_sqm = area

    db.commit()
    db.refresh(camera)
    return camera

@router.put("/{camera_id}/active-zone", response_model=CameraResponse)
def set_active_zone(
    camera_id: int, payload: ActiveZoneUpdate, db: Session = Depends(get_db)
):
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera with id {camera_id} not found",
        )

    if payload.zone_id is None:
        camera.active_zone_id = None  # back to full-frame mode
    else:
        zone = db.get(Zone, payload.zone_id)
        if zone is None:
            raise HTTPException(
                status_code=404,
                detail=f"Zone with id {payload.zone_id} not found",
            )
        if zone.camera_id != camera.id:
            raise HTTPException(
                status_code=400,
                detail=f"Zone {zone.id} belongs to camera {zone.camera_id}, not camera {camera.id}",
            )
        camera.active_zone_id = zone.id

    db.commit()
    db.refresh(camera)
    return camera