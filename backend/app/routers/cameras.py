from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.camera import Camera
from app.models.event import Event
from app.schemas.camera import CameraCreate, CameraResponse, SourceCheckResponse
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