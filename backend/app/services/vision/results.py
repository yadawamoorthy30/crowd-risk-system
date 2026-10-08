from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class TrackedPerson:
    track_id: int
    confidence: float
    x: int          # left edge of the box
    y: int          # top edge of the box
    width: int
    height: int
    foot_x: int     # bottom-centre of the box = where the person stands
    foot_y: int
    counted: bool = True   # inside the monitored area, so part of N(t)


@dataclass
class FrameMetrics:
    mode: str                          # "full_frame" | "zone"
    zone_id: Optional[int]
    zone_name: Optional[str]
    area_sqm: Optional[float]
    people_count: int                  # N(t)
    people_count_smoothed: float
    density: Optional[float]           # D(t) in people per m2
    density_smoothed: Optional[float]
    message: Optional[str] = None      # "Area not configured" when density is None


@dataclass
class FrameResult:
    frame_number: int       # index in the source video/stream
    timestamp: datetime
    people: List[TrackedPerson] = field(default_factory=list)
    frame_width: int = 0    # size of the processed frame the boxes refer to
    frame_height: int = 0
    metrics: Optional[FrameMetrics] = None

    @property
    def people_detected(self) -> int:
        return len(self.people)