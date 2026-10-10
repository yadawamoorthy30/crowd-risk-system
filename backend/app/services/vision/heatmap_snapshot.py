"""What is saved for one heatmap snapshot (SRS 8.1.8, FR-HMP-004).

No database access here: this builds the row values, the file name and the
heatmap-only PNG. Writing them is done in persistence.py.
"""
from datetime import datetime

import numpy as np

from app.services.vision.heatmap import MODES, normalise, window_seconds
from app.services.vision.heatmap_render import (
    encode_png, heatmap_image_size, render_heatmap_image,
)


def heatmap_fields(calc, mode: str, ts: datetime) -> dict:
    """Column values for one heatmap_snapshots row: aggregated cell values only."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    grid = calc.grid(mode).astype(np.float64)
    return {
        "ts": ts,
        "mode": mode.upper(),                       # INSTANT / WINDOW
        "window_sec": int(window_seconds(calc.window_minutes)) if mode == "window" else None,
        "grid_cols": calc.cols,
        "grid_rows": calc.rows,
        "grid_data": np.round(grid, 2).tolist(),    # rows x cols
    }


def build_image_path(camera_id: int, ts: datetime, mode: str) -> str:
    """Path relative to backend/storage, always with forward slashes."""
    stamp = ts.strftime("%Y%m%d_%H%M%S") + f"_{ts.microsecond // 1000:03d}"
    return f"heatmaps/camera_{camera_id}/{stamp}_{mode}.png"


def render_snapshot_png(calc, mode: str, frame_w: int, frame_h: int) -> bytes:
    """PNG bytes of the heatmap alone (black background, colour legend)."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    width, height = heatmap_image_size(frame_w, frame_h)
    if mode == "instant":
        title = "Heatmap: instant (people per cell)"
    else:
        title = f"Heatmap: last {calc.window_minutes} min (avg people per cell)"
    detail = f"busiest cell: {calc.peak(mode):.1f}"
    image = render_heatmap_image(normalise(calc.grid(mode)), width, height, title, detail)
    return encode_png(image)