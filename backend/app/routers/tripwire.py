from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.camera import Camera
from app.models.tripwire import Tripwire
from app.schemas.tripwire import TripwireResponse, TripwireUpdate

router = APIRouter(
    prefix="/api/cameras",
    tags=["Tripwire"],
)


def _dec(value: float) -> Decimal:
    # match DECIMAL(6,5): 5 digits after the point
    return Decimal(str(value)).quantize(Decimal("0.00001"))


def _require_camera(db: Session, camera_id: int) -> Camera:
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera with id {camera_id} not found",
        )
    return camera


@router.put(
    "/{camera_id}/tripwire",
    response_model=TripwireResponse,
)
def set_tripwire(
    camera_id: int,
    payload: TripwireUpdate,
    db: Session = Depends(get_db),
):
    _require_camera(db, camera_id)

    tripwire = (
        db.query(Tripwire).filter(Tripwire.camera_id == camera_id).first()
    )

    if tripwire is None:
        tripwire = Tripwire(camera_id=camera_id)
        db.add(tripwire)

    tripwire.x1 = _dec(payload.x1)
    tripwire.y1 = _dec(payload.y1)
    tripwire.x2 = _dec(payload.x2)
    tripwire.y2 = _dec(payload.y2)
    tripwire.in_side = payload.in_side
    tripwire.cooldown_sec = payload.cooldown_sec

    db.commit()
    db.refresh(tripwire)

    return tripwire


@router.get(
    "/{camera_id}/tripwire",
    response_model=TripwireResponse,
)
def get_tripwire(
    camera_id: int,
    db: Session = Depends(get_db),
):
    _require_camera(db, camera_id)

    tripwire = (
        db.query(Tripwire).filter(Tripwire.camera_id == camera_id).first()
    )

    if tripwire is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera {camera_id} has no tripwire configured",
        )

    return tripwire