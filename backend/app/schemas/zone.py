from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def validate_polygon(points: List[List[float]]) -> List[List[float]]:
    if len(points) < 3:
        raise ValueError("polygon needs at least 3 points")
    for p in points:
        if len(p) != 2:
            raise ValueError("each polygon point must be [x, y]")
        x, y = p
        # written so NaN/Infinity also fail
        if not (0 <= x <= 1 and 0 <= y <= 1):
            raise ValueError("polygon coordinates must be between 0 and 1")
    # shoelace formula: reject points that are all on one line
    n = len(points)
    twice_area = sum(
        points[i][0] * points[(i + 1) % n][1] - points[(i + 1) % n][0] * points[i][1]
        for i in range(n)
    )
    if abs(twice_area) / 2 < 1e-4:
        raise ValueError("polygon has no area (points are in a line or too close)")
    return [[float(x), float(y)] for x, y in points]


class ZoneCreate(BaseModel):
    camera_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=100)
    polygon: List[List[float]]
    area_sqm: float = Field(..., gt=0, le=99999999.99, allow_inf_nan=False)

    @field_validator("polygon")
    @classmethod
    def check_polygon(cls, v):
        return validate_polygon(v)


class ZoneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    polygon: Optional[List[List[float]]] = None
    area_sqm: Optional[float] = Field(None, gt=0, le=99999999.99, allow_inf_nan=False)

    @field_validator("polygon")
    @classmethod
    def check_polygon(cls, v):
        return validate_polygon(v) if v is not None else v

    @model_validator(mode="after")
    def at_least_one(self):
        if self.name is None and self.polygon is None and self.area_sqm is None:
            raise ValueError("Send at least one of name, polygon, area_sqm")
        return self


class ZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    name: str
    polygon: List[List[float]]
    area_sqm: float
    is_active: bool
    created_at: datetime