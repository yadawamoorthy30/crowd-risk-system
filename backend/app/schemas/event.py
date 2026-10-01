from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    location: str = Field(..., min_length=1, max_length=255)
    event_date: date
    description: Optional[str] = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    event_date: date
    description: Optional[str] = None
    created_at: datetime