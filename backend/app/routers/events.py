from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.event import Event
from app.schemas.event import EventCreate, EventResponse

router = APIRouter(prefix="/api/events", tags=["Events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    event = Event(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("", response_model=List[EventResponse])
def list_events(db: Session = Depends(get_db)):
    return db.query(Event).order_by(Event.id).all()