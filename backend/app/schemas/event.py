from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.event import EventStatus


class EventCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    event_type: str = Field("GENERAL", min_length=1, max_length=50)
    venue: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    status: EventStatus = EventStatus.PLANNED
    created_by: Optional[int] = Field(None, gt=0)

    @model_validator(mode="after")
    def check_times(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    event_type: str
    venue: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    status: EventStatus
    created_by: Optional[int] = None
    created_at: datetime