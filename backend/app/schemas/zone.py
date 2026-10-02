from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ZoneCreate(BaseModel):
    camera_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=100)
    area_sq_m: float = Field(..., gt=0, le=99999999.99)


class ZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    name: str
    area_sq_m: float
    created_at: datetime