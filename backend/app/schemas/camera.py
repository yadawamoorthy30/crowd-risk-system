from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.camera import SourceType


class CameraCreate(BaseModel):
    event_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=100)
    source_type: SourceType
    source_path: str = Field(..., min_length=1, max_length=500)
    location_description: Optional[str] = Field(None, max_length=255)
    is_active: bool = True

    @model_validator(mode="after")
    def check_source_path(self):
        if self.source_type == SourceType.webcam and not self.source_path.isdigit():
            raise ValueError("For a webcam, source_path must be the camera index, e.g. '0'")
        if self.source_type == SourceType.rtsp and not self.source_path.lower().startswith("rtsp://"):
            raise ValueError("For an rtsp camera, source_path must start with rtsp://")
        return self


class CameraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    name: str
    source_type: SourceType
    source_path: str
    location_description: Optional[str] = None
    is_active: bool
    created_at: datetime