from dataclasses import dataclass
from pathlib import Path

# backend/app/services/vision/config.py -> backend is 3 levels up
BACKEND_DIR = Path(__file__).resolve().parents[3]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_MODEL_PATH = BACKEND_DIR / "models" / "yolo26n.pt"

PERSON_CLASS_ID = 0  # COCO class 0 = person
SNAPSHOT_INTERVAL_SECONDS = 1.0  # how often a sample is saved to MySQL


@dataclass
class VisionConfig:
    model_path: str = str(DEFAULT_MODEL_PATH)
    tracker: str = "bytetrack.yaml"
    conf: float = 0.40            # SRS default; the API passes the camera's value
    imgsz: int = 640
    track_buffer: int = 30        # frames a lost track is remembered
    process_width: int = 1280     # frames are scaled to FIT inside this box
    process_height: int = 720
    target_fps: int = 10          # analysis rate, from cameras.processing_fps
    realtime: bool = False        # True = also drop frames when we fall behind
    history_length: int = 30      # positions kept per track
    smoothing_seconds: float = 5.0  # window for the N(t) / D(t) moving average
    initial_count: int = 0           # people already inside when detection starts
    flow_window_sec: float = 60.0    # rolling window for IN/OUT and net flow F(t)
    growth_window_sec: float = 60.0  # dt for R(t); minimum 10 s
    heatmap_cols: int = 32          # grid size (FR-HMP-001)
    heatmap_rows: int = 18
    heatmap_window_min: int = 5     # window mode: 1, 5, 15 or 30 minutes (FR-HMP-002)
    occupancy_tolerance_pct: float = 30.0
    occupancy_min_difference: float = 3.0
    heatmap_save_interval_sec: int = 60     # seconds between saved heatmaps; 0 = off (FR-HMP-004)
    heatmap_save_mode: str = "window"       # which heatmap is saved: "window" or "instant"