from decimal import Decimal
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.camera import CameraStatus, SourceType


class CameraCreate(BaseModel):
    event_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=100)
    source_type: SourceType
    source_path: str = Field(..., min_length=1, max_length=500)
    location_description: Optional[str] = Field(None, max_length=255)
    min_confidence: float = Field(0.40, gt=0, le=1)
    processing_fps: int = Field(10, ge=1, le=60)

    @model_validator(mode="after")
    def check_source_path(self):
        path = self.source_path.strip().lower()
        if self.source_type == SourceType.USB and not path.isdigit():
            raise ValueError("For a USB camera, source_path must be the camera index, e.g. '0'")
        if self.source_type == SourceType.RTSP and not path.startswith("rtsp://"):
            raise ValueError("For an RTSP camera, source_path must start with rtsp://")
        if self.source_type == SourceType.HTTP and not path.startswith(("http://", "https://")):
            raise ValueError("For an HTTP camera, source_path must start with http:// or https://")
        return self


class CameraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    name: str
    source_type: SourceType
    source_path: str
    location_description: Optional[str] = None
    area_length_m: Optional[float] = None
    area_width_m: Optional[float] = None
    area_sqm: Optional[float] = None
    min_confidence: float
    processing_fps: int
    status: CameraStatus
    active_zone_id: Optional[int] = None
    created_at: datetime


class SourceCheckResponse(BaseModel):
    camera_id: int
    source_type: str
    source_path: str
    reachable: Optional[bool] = None
    message: str
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    frame_count: Optional[int] = None

class CameraAreaUpdate(BaseModel):
    area_length_m: Optional[float] = Field(None, gt=0, le=1000, allow_inf_nan=False)
    area_width_m: Optional[float] = Field(None, gt=0, le=1000, allow_inf_nan=False)
    area_sqm: Optional[float] = Field(None, gt=0, le=1_000_000, allow_inf_nan=False)

    @model_validator(mode="after")
    def check_mode(self):
        has_dims = self.area_length_m is not None or self.area_width_m is not None
        has_area = self.area_sqm is not None
        if has_dims and has_area:
            raise ValueError("Send either length and width, or area_sqm, not both")
        if has_dims and (self.area_length_m is None or self.area_width_m is None):
            raise ValueError("Both area_length_m and area_width_m are required")
        if not has_dims and not has_area:
            raise ValueError("Send area_length_m + area_width_m, or area_sqm")
        return self

    def computed_area(self) -> Decimal:
        if self.area_sqm is not None:
            area = Decimal(str(self.area_sqm))
        else:
            area = Decimal(str(self.area_length_m)) * Decimal(str(self.area_width_m))
        return area.quantize(Decimal("0.01"))

class ActiveZoneUpdate(BaseModel):
    # required key, but the value may be null (= full frame)
    zone_id: Optional[int] = Field(..., gt=0)