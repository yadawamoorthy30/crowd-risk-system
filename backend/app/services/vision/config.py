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