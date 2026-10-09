"""Net flow, cumulative occupancy and growth rate (SRS FR-FLW-004/005).

Pure logic: no OpenCV, no database. All times are VIDEO seconds.
"""
from collections import deque
from dataclasses import dataclass
from typing import Optional, Tuple

MIN_GROWTH_WINDOW_SEC = 10.0   # SRS: minimum dt for R(t)


def rolling_in_out(events, now: float, window_sec: float) -> Tuple[int, int]:
    """Crossings inside the window (now - window_sec, now]."""
    start = now - window_sec
    rolling_in = rolling_out = 0
    for event in events:
        if start < event.video_time <= now:
            if event.direction == "IN":
                rolling_in += 1
            elif event.direction == "OUT":
                rolling_out += 1
    return rolling_in, rolling_out


def net_flow(rolling_in: int, rolling_out: int) -> int:
    """F(t) = IN - OUT. Positive means the crowd is growing."""
    return rolling_in - rolling_out


def cumulative_occupancy(initial_count: int, in_total: int, out_total: int) -> int:
    """initial count + sum(IN) - sum(OUT). Deliberately not clamped at 0."""
    return initial_count + in_total - out_total


class GrowthRateCalculator:
    """R(t) = [N(t) - N(t-dt)] / dt in people per minute.

    Keeps only the samples it needs: the latest one at or before (now - dt),
    and everything after it.
    """

    def __init__(self, window_sec: float = 60.0):
        if window_sec < MIN_GROWTH_WINDOW_SEC:
            raise ValueError(f"growth window must be at least {MIN_GROWTH_WINDOW_SEC:g} s")
        self.window_sec = float(window_sec)
        self.last_window_sec = 0.0       # span actually used by the last update
        self._items = deque()            # (video_time, N)

    def update(self, n: float, video_time: float) -> Optional[float]:
        """Add the newest N(t). Returns people/minute, or None while warming up."""
        self._items.append((video_time, n))
        while len(self._items) >= 2 and self._items[1][0] <= video_time - self.window_sec:
            self._items.popleft()

        t0, n0 = self._items[0]
        elapsed = video_time - t0
        self.last_window_sec = elapsed
        if elapsed < MIN_GROWTH_WINDOW_SEC:
            return None
        return (n - n0) / (elapsed / 60.0)


@dataclass(frozen=True)
class FlowMetrics:
    video_time: float
    tripwire_configured: bool
    in_total: Optional[int] = None
    out_total: Optional[int] = None
    rolling_in: Optional[int] = None
    rolling_out: Optional[int] = None
    net_flow: Optional[int] = None
    flow_window_sec: Optional[float] = None
    initial_count: Optional[int] = None
    cumulative_occupancy: Optional[int] = None
    growth_rate: Optional[float] = None          # people per minute
    growth_window_sec: Optional[float] = None    # window actually used
    message: Optional[str] = None                # tripwire message
    growth_message: Optional[str] = None


class FlowMetricsCalculator:
    def __init__(self, initial_count: int = 0, flow_window_sec: float = 60.0,
                 growth_window_sec: float = 60.0):
        if initial_count < 0:
            raise ValueError("initial_count must be 0 or more")
        if flow_window_sec <= 0:
            raise ValueError("flow window must be positive")
        self.initial_count = initial_count
        self.flow_window_sec = float(flow_window_sec)
        self._growth = GrowthRateCalculator(growth_window_sec)

    def update(self, counter, n_smoothed: float, video_time: float) -> FlowMetrics:
        """counter: a TripwireCounter (in_total, out_total, events) or None."""
        growth = self._growth.update(n_smoothed, video_time)
        common = dict(
            video_time=round(video_time, 2),
            flow_window_sec=self.flow_window_sec,
            initial_count=self.initial_count,
            growth_rate=None if growth is None else round(growth, 2),
            growth_window_sec=round(self._growth.last_window_sec, 1),
            growth_message=None if growth is not None else
            f"Growth rate not available yet (needs {MIN_GROWTH_WINDOW_SEC:g} s of data)",
        )

        if counter is None:
            return FlowMetrics(tripwire_configured=False,
                               message="Tripwire not configured", **common)

        rolling_in, rolling_out = rolling_in_out(
            counter.events, video_time, self.flow_window_sec)
        return FlowMetrics(
            tripwire_configured=True,
            in_total=counter.in_total,
            out_total=counter.out_total,
            rolling_in=rolling_in,
            rolling_out=rolling_out,
            net_flow=net_flow(rolling_in, rolling_out),
            cumulative_occupancy=cumulative_occupancy(
                self.initial_count, counter.in_total, counter.out_total),
            **common,
        )