import time
from collections import deque
from dataclasses import dataclass
from typing import List, Optional

from app.services.vision.results import FrameMetrics

AREA_NOT_CONFIGURED = "Area not configured"


@dataclass
class MonitorArea:
    """What one camera is monitoring: the full frame, or one selected zone."""
    mode: str = "full_frame"                 # "full_frame" | "zone"
    area_sqm: Optional[float] = None         # A (zone area, or camera area)
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None
    polygon: Optional[List[List[float]]] = None  # normalised points, zone mode only


def foot_point(x1: int, y1: int, x2: int, y2: int):
    """Bottom-centre of a bounding box = where the person stands."""
    return (x1 + x2) // 2, y2


def point_in_polygon(x: float, y: float, polygon) -> bool:
    """Ray casting: count how many polygon edges a ray to the right crosses."""
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def compute_density(count: int, area_sqm: Optional[float]) -> Optional[float]:
    """D = N / A in people per square metre, or None if no usable area."""
    if area_sqm is None or area_sqm <= 0:
        return None
    return count / area_sqm


class MovingAverage:
    """Average of the values added during the last `window_seconds`."""

    def __init__(self, window_seconds: float):
        self._window = window_seconds
        self._items = deque()  # (time, value)

    def add(self, value: float, now: Optional[float] = None) -> float:
        now = time.monotonic() if now is None else now
        self._items.append((now, value))
        cutoff = now - self._window
        while len(self._items) > 1 and self._items[0][0] < cutoff:
            self._items.popleft()
        return sum(v for _t, v in self._items) / len(self._items)


class MetricsCalculator:
    def __init__(self, monitor: MonitorArea, smoothing_seconds: float = 5.0):
        self.monitor = monitor
        self._n_avg = MovingAverage(smoothing_seconds)
        self._d_avg = MovingAverage(smoothing_seconds)

    def update(self, people, frame_width: int, frame_height: int,
               now: Optional[float] = None) -> FrameMetrics:
        monitor = self.monitor
        use_zone = monitor.mode == "zone" and bool(monitor.polygon)

        count = 0
        for person in people:
            if use_zone:
                person.counted = point_in_polygon(
                    person.foot_x / frame_width,    # pixels -> 0..1
                    person.foot_y / frame_height,
                    monitor.polygon,
                )
            else:
                person.counted = True
            if person.counted:
                count += 1

        density = compute_density(count, monitor.area_sqm)
        count_avg = self._n_avg.add(count, now)
        density_avg = self._d_avg.add(density, now) if density is not None else None

        return FrameMetrics(
            mode="zone" if use_zone else "full_frame",
            zone_id=monitor.zone_id if use_zone else None,
            zone_name=monitor.zone_name if use_zone else None,
            area_sqm=monitor.area_sqm,
            people_count=count,
            people_count_smoothed=round(count_avg, 2),
            density=None if density is None else round(density, 4),
            density_smoothed=None if density_avg is None else round(density_avg, 4),
            message=AREA_NOT_CONFIGURED if density is None else None,
        )