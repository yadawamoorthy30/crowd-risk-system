from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.camera import Camera
from app.models.zone import Zone
from app.schemas.zone import ZoneCreate, ZoneResponse, ZoneUpdate

router = APIRouter(prefix="/api/zones", tags=["Zones"])


@router.post("", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
def create_zone(payload: ZoneCreate, db: Session = Depends(get_db)):
    camera = db.get(Camera, payload.camera_id)
    if camera is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera with id {payload.camera_id} not found",
        )

    zone = Zone(**payload.model_dump())
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.get("", response_model=List[ZoneResponse])
def list_zones(camera_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Zone)
    if camera_id is not None:
        query = query.filter(Zone.camera_id == camera_id)
    return query.order_by(Zone.id).all()


@router.put("/{zone_id}", response_model=ZoneResponse)
def update_zone(zone_id: int, payload: ZoneUpdate, db: Session = Depends(get_db)):
    zone = db.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail=f"Zone with id {zone_id} not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(zone, field, value)
    db.commit()
    db.refresh(zone)
    return zone