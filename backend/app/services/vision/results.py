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


@dataclass
class FrameResult:
    frame_number: int
    timestamp: datetime
    people: List[TrackedPerson] = field(default_factory=list)

    @property
    def people_detected(self) -> int:
        return len(self.people)