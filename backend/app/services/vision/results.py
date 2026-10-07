from dataclasses import dataclass, field
from datetime import datetime
from typing import List


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


@dataclass
class FrameResult:
    frame_number: int       # index in the source video/stream
    timestamp: datetime
    people: List[TrackedPerson] = field(default_factory=list)
    frame_width: int = 0    # size of the processed frame the boxes refer to
    frame_height: int = 0

    @property
    def people_detected(self) -> int:
        return len(self.people)