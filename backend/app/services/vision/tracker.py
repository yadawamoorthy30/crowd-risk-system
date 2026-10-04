from collections import defaultdict, deque
from datetime import datetime

from app.services.vision.results import FrameResult, TrackedPerson


class TrackManager:
    """Turns raw tracker output into clean results and remembers each track's path."""

    def __init__(self, trail_length: int = 30):
        self._trails = defaultdict(lambda: deque(maxlen=trail_length))
        self._seen_ids = set()

    def update(self, boxes, frame_number: int) -> FrameResult:
        people = []

        if boxes.id is not None:
            track_ids = boxes.id.int().tolist()
            for box, track_id in zip(boxes, track_ids):
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                people.append(
                    TrackedPerson(
                        track_id=track_id,
                        confidence=round(float(box.conf[0]), 3),
                        x=x1,
                        y=y1,
                        width=x2 - x1,
                        height=y2 - y1,
                    )
                )
                self._seen_ids.add(track_id)
                self._trails[track_id].append(((x1 + x2) // 2, y2))  # bottom-centre

        return FrameResult(frame_number=frame_number, timestamp=datetime.now(), people=people)

    def trail(self, track_id: int):
        return list(self._trails[track_id])

    @property
    def unique_ids(self) -> int:
        return len(self._seen_ids)