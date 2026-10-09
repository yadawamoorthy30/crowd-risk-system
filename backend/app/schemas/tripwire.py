from datetime import datetime
from math import hypot

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.tripwire import InSide

# Frames are scaled to fit 1280x720, so height = 0.5625 x width.
FRAME_ASPECT = 720 / 1280
# SRS section 14: tripwire must be at least 20% of the frame width.
MIN_LENGTH_FRAC = 0.20


def line_length_in_frame_widths(x1: float, y1: float, x2: float, y2: float) -> float:
    """Length of the line, measured in units of frame width (assumes 16:9)."""
    dx = x2 - x1
    dy = (y2 - y1) * FRAME_ASPECT
    return hypot(dx, dy)


class TripwireUpdate(BaseModel):
    x1: float = Field(..., ge=0, le=1, allow_inf_nan=False)
    y1: float = Field(..., ge=0, le=1, allow_inf_nan=False)
    x2: float = Field(..., ge=0, le=1, allow_inf_nan=False)
    y2: float = Field(..., ge=0, le=1, allow_inf_nan=False)
    in_side: InSide
    cooldown_sec: int = Field(3, ge=0, le=60)

    @model_validator(mode="after")
    def check_length(self):
        length = line_length_in_frame_widths(self.x1, self.y1, self.x2, self.y2)
        # small tolerance so a line of exactly 20% is not rejected by float error
        if length < MIN_LENGTH_FRAC - 1e-9:
            raise ValueError(
                f"Tripwire is too short: {length * 100:.1f}% of the frame width "
                f"(minimum is {MIN_LENGTH_FRAC * 100:.0f}%)"
            )
        return self


class TripwireResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    x1: float
    y1: float
    x2: float
    y2: float
    in_side: InSide
    cooldown_sec: int
    created_at: datetime
    updated_at: datetime