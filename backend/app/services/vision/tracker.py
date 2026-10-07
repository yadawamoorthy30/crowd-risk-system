import time
from collections import deque
from datetime import datetime

from app.services.vision.results import FrameResult, TrackedPerson


class TrackManager:
    """Turns raw tracker output into clean results and keeps an in-memory
    position history for ACTIVE tracks only (anonymous, never stored)."""

    def __init__(self, history_length: int = 30, track_buffer: int = 30):
        self._history = {}      # track_id -> deque[(time, foot_x, foot_y)]
        self._last_seen = {}    # track_id -> update number it was last seen in
        self._seen_ids = set()
        self._history_length = history_length
        self._track_buffer = track_buffer
        self._updates = 0       # counts processed frames (skipped ones never arrive)

    def update(self, boxes, frame_number: int, frame_width: int, frame_height: int) -> FrameResult:
        self._updates += 1
        people = []

        if boxes.id is not None:
            track_ids = boxes.id.int().tolist()
            for box, track_id in zip(boxes, track_ids):
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                foot_x, foot_y = (x1 + x2) // 2, y2  # bottom-centre
                people.append(
                    TrackedPerson(
                        track_id=track_id,
                        confidence=round(float(box.conf[0]), 3),
                        x=x1, y=y1, width=x2 - x1, height=y2 - y1,
                        foot_x=foot_x, foot_y=foot_y,
                    )
                )
                self._seen_ids.add(track_id)
                history = self._history.get(track_id)
                if history is None:
                    history = deque(maxlen=self._history_length)
                    self._history[track_id] = history
                history.append((time.time(), foot_x, foot_y))
                self._last_seen[track_id] = self._updates

        self._prune()
        return FrameResult(
            frame_number=frame_number,
            timestamp=datetime.now(),
            people=people,
            frame_width=frame_width,
            frame_height=frame_height,
        )

    def _prune(self):
        stale = [tid for tid, seen in self._last_seen.items()
                 if self._updates - seen > self._track_buffer]
        for tid in stale:
            del self._last_seen[tid]
            del self._history[tid]

    def trail(self, track_id: int):
        """Foot positions as (x, y), oldest first, for drawing."""
        return [(x, y) for _t, x, y in self._history.get(track_id, ())]

    def history(self, track_id: int):
        """Foot positions with timestamps, for later speed/flow work."""
        return list(self._history.get(track_id, ()))

    @property
    def unique_ids(self) -> int:
        return len(self._seen_ids)

    @property
    def tracks_in_memory(self) -> int:
        return len(self._history)