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
    conf: float = 0.25
    imgsz: int = 640