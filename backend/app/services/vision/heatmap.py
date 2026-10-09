"""Grid heatmap from foot points (SRS FR-HMP-001/002).

Pure NumPy: no OpenCV, no database. Times are VIDEO seconds.
Rows follow y (top to bottom), columns follow x (left to right).
"""
from collections import deque
from typing import Iterable, Optional, Tuple

import numpy as np

DEFAULT_COLS = 32
DEFAULT_ROWS = 18
ALLOWED_WINDOW_MINUTES = (1, 5, 15, 30)
DEFAULT_WINDOW_MINUTES = 5
MODES = ("instant", "window")


def window_seconds(minutes) -> float:
    if minutes not in ALLOWED_WINDOW_MINUTES:
        raise ValueError(f"heatmap window must be one of {ALLOWED_WINDOW_MINUTES} minutes")
    return float(minutes) * 60.0


def cell_index(x: float, y: float, frame_w: int, frame_h: int,
               cols: int, rows: int) -> Optional[Tuple[int, int]]:
    """(row, col) of the grid cell containing the point, or None if outside the frame."""
    if frame_w <= 0 or frame_h <= 0:
        return None
    if x < 0 or y < 0 or x > frame_w or y > frame_h:
        return None
    col = min(int(x / frame_w * cols), cols - 1)   # x == frame_w belongs to the last cell
    row = min(int(y / frame_h * rows), rows - 1)
    return row, col


def instant_grid(points: Iterable[Tuple[float, float]], frame_w: int, frame_h: int,
                 cols: int = DEFAULT_COLS, rows: int = DEFAULT_ROWS) -> np.ndarray:
    """People per cell for one frame."""
    grid = np.zeros((rows, cols), dtype=np.int32)
    for x, y in points:
        cell = cell_index(x, y, frame_w, frame_h, cols, rows)
        if cell is not None:
            grid[cell] += 1
    return grid


def normalise(grid: np.ndarray) -> np.ndarray:
    """Scale to 0..1 by the busiest cell (an all-zero grid stays zero)."""
    peak = float(np.max(grid)) if grid.size else 0.0
    if peak <= 0:
        return np.zeros(grid.shape, dtype=np.float32)
    return (grid / peak).astype(np.float32)


class WindowAccumulator:
    """Average people per frame in each cell over the last `window_sec` video seconds."""

    def __init__(self, cols: int, rows: int, window_sec: float):
        self.window_sec = float(window_sec)
        self._shape = (rows, cols)
        self._buckets = deque()                       # [second, summed grid, frame count]
        self._sum = np.zeros(self._shape, dtype=np.int64)
        self._frames = 0

    def add(self, grid: np.ndarray, video_time: float) -> None:
        second = int(video_time)
        if self._buckets and self._buckets[-1][0] == second:
            bucket = self._buckets[-1]
            bucket[1] += grid
            bucket[2] += 1
        else:
            self._buckets.append([second, grid.astype(np.int64), 1])
        self._sum += grid
        self._frames += 1

        cutoff = video_time - self.window_sec
        while self._buckets and self._buckets[0][0] + 1 <= cutoff:   # whole bucket too old
            _second, old_grid, old_frames = self._buckets.popleft()
            self._sum -= old_grid
            self._frames -= old_frames

    def mean_grid(self) -> np.ndarray:
        if self._frames == 0:
            return np.zeros(self._shape, dtype=np.float32)
        return (self._sum / self._frames).astype(np.float32)

    @property
    def frames(self) -> int:
        return self._frames

    @property
    def buckets(self) -> int:
        return len(self._buckets)


class HeatmapCalculator:
    def __init__(self, cols: int = DEFAULT_COLS, rows: int = DEFAULT_ROWS,
                 window_minutes: int = DEFAULT_WINDOW_MINUTES):
        if not 4 <= cols <= 128 or not 4 <= rows <= 128:
            raise ValueError("heatmap grid must be between 4 and 128 cells per side")
        self.cols = cols
        self.rows = rows
        self.window_minutes = window_minutes
        self._acc = WindowAccumulator(cols, rows, window_seconds(window_minutes))
        self._instant = np.zeros((rows, cols), dtype=np.int32)

    def update(self, points, frame_w: int, frame_h: int, video_time: float) -> None:
        self._instant = instant_grid(points, frame_w, frame_h, self.cols, self.rows)
        self._acc.add(self._instant, video_time)

    def grid(self, mode: str) -> np.ndarray:
        if mode == "instant":
            return self._instant.astype(np.float32)
        if mode == "window":
            return self._acc.mean_grid()
        raise ValueError(f"mode must be one of {MODES}")

    def peak(self, mode: str) -> float:
        return float(self.grid(mode).max())