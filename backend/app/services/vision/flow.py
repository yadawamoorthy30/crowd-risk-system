"""Tripwire IN/OUT counting (SRS FR-FLW-001/002/003/006).

Pure logic: no OpenCV, no database. Works in pixel coordinates of the
processed frame. Track IDs live only in memory.
"""
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from math import hypot
from typing import Optional

HYSTERESIS_FRAC = 0.01      # half-width of the dead band, as a fraction of frame width
PROJECTION_MARGIN = 0.02    # tolerance at the ends of the drawn segment


@dataclass(frozen=True)
class TripwireLine:
    x1: float
    y1: float
    x2: float
    y2: float
    in_side: str = "RIGHT"        # LEFT or RIGHT, relative to walking p1 -> p2
    cooldown_sec: float = 3.0

    def __post_init__(self):
        if self.in_side.upper() not in ("LEFT", "RIGHT"):
            raise ValueError("in_side must be LEFT or RIGHT")

    @property
    def in_sign(self) -> int:
        """+1 if the IN side is RIGHT (positive distance), -1 if LEFT."""
        return 1 if self.in_side.upper() == "RIGHT" else -1

    @classmethod
    def from_model(cls, tripwire) -> "TripwireLine":
        """Build from the database row (Decimal values, Enum in_side)."""
        side = getattr(tripwire.in_side, "value", tripwire.in_side)
        return cls(
            float(tripwire.x1), float(tripwire.y1),
            float(tripwire.x2), float(tripwire.y2),
            in_side=str(side), cooldown_sec=float(tripwire.cooldown_sec),
        )


@dataclass(frozen=True)
class TrackState:
    side: Optional[int] = None            # last confirmed side: +1 / -1 / None
    last_crossing: Optional[float] = None  # video time of the last counted crossing


@dataclass(frozen=True)
class CrossingEvent:
    timestamp: datetime     # wall clock
    video_time: float       # seconds into the video
    direction: str          # "IN" or "OUT"  (no track id, FR-FLW-006)


def signed_distance(px, py, ax, ay, bx, by) -> float:
    """Pixels from the line A->B. Positive = RIGHT side, negative = LEFT side."""
    dx, dy = bx - ax, by - ay
    length = hypot(dx, dy)
    if length == 0:
        return 0.0
    return (dx * (py - ay) - dy * (px - ax)) / length


def projection(px, py, ax, ay, bx, by) -> float:
    """Where the point falls along the segment: 0 = at A, 1 = at B."""
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    if denom == 0:
        return 0.0
    return ((px - ax) * dx + (py - ay) * dy) / denom


def step_track(state, distance, along, now, band, cooldown, in_sign):
    """One update for one track. Returns (new_state, 'IN' | 'OUT' | None)."""
    if distance > band:
        observed = 1
    elif distance < -band:
        observed = -1
    else:
        return state, None                    # inside the band: keep last side

    if state.side is None:                    # first clear sighting: never a crossing
        return TrackState(observed, state.last_crossing), None
    if observed == state.side:
        return state, None

    if state.last_crossing is not None and now - state.last_crossing < cooldown:
        return state, None                    # cooldown: look again next frame

    if not (-PROJECTION_MARGIN <= along <= 1 + PROJECTION_MARGIN):
        # went around the end of the line, not across it
        return TrackState(observed, state.last_crossing), None

    direction = "IN" if observed == in_sign else "OUT"
    return TrackState(observed, now), direction


class TripwireCounter:
    def __init__(self, line: TripwireLine, forget_after: int = 30, max_events: int = 10_000):
        self.line = line
        self._forget_after = forget_after
        self._states = {}        # track_id -> TrackState   (memory only)
        self._last_seen = {}     # track_id -> update number
        self._updates = 0
        self._in = 0
        self._out = 0
        self._events = deque(maxlen=max_events)

    def update(self, people, frame_width, frame_height, video_time):
        """people: objects with track_id, foot_x, foot_y. Returns new CrossingEvents."""
        self._updates += 1
        ln = self.line
        ax, ay = ln.x1 * frame_width, ln.y1 * frame_height
        bx, by = ln.x2 * frame_width, ln.y2 * frame_height
        band = HYSTERESIS_FRAC * frame_width
        new_events = []

        for p in people:
            distance = signed_distance(p.foot_x, p.foot_y, ax, ay, bx, by)
            along = projection(p.foot_x, p.foot_y, ax, ay, bx, by)
            state, direction = step_track(
                self._states.get(p.track_id, TrackState()),
                distance, along, video_time, band, ln.cooldown_sec, ln.in_sign,
            )
            self._states[p.track_id] = state
            self._last_seen[p.track_id] = self._updates

            if direction is not None:
                if direction == "IN":
                    self._in += 1
                else:
                    self._out += 1
                event = CrossingEvent(datetime.now(), video_time, direction)
                self._events.append(event)
                new_events.append(event)

        stale = [t for t, seen in self._last_seen.items()
                 if self._updates - seen > self._forget_after]
        for t in stale:
            del self._last_seen[t]
            del self._states[t]
        return new_events

    @property
    def in_total(self) -> int:
        return self._in

    @property
    def out_total(self) -> int:
        return self._out

    @property
    def events(self):
        return list(self._events)

    @property
    def tracked_count(self) -> int:
        return len(self._states)