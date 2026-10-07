import os
import tempfile

import yaml
from ultralytics import YOLO
from ultralytics.utils import ROOT

from app.services.vision.config import PERSON_CLASS_ID, VisionConfig

# used only if Ultralytics' own bytetrack.yaml cannot be found
FALLBACK_BYTETRACK = {
    "tracker_type": "bytetrack",
    "track_high_thresh": 0.25,
    "track_low_thresh": 0.1,
    "new_track_thresh": 0.25,
    "match_thresh": 0.8,
    "fuse_score": True,
}


class PersonDetector:
    """Loads the YOLO model and runs person detection + tracking on one frame.

    Tracker memory lives inside this object, so use ONE detector per camera.
    """

    def __init__(self, config: VisionConfig):
        self.config = config
        self.model = YOLO(config.model_path)
        self._temp_cfg = None
        self._tracker_cfg = self._build_tracker_cfg()

    def _build_tracker_cfg(self) -> str:
        # other trackers (e.g. botsort.yaml) are used exactly as given
        if self.config.tracker != "bytetrack.yaml":
            return self.config.tracker

        base = ROOT / "cfg" / "trackers" / "bytetrack.yaml"
        if base.is_file():
            settings = yaml.safe_load(base.read_text(encoding="utf-8"))
        else:
            settings = dict(FALLBACK_BYTETRACK)

        conf = self.config.conf
        settings["track_buffer"] = self.config.track_buffer
        settings["track_high_thresh"] = conf
        settings["new_track_thresh"] = conf
        settings["track_low_thresh"] = min(settings.get("track_low_thresh", 0.1), conf)

        fd, path = tempfile.mkstemp(prefix="bytetrack_", suffix=".yaml")
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            yaml.safe_dump(settings, file)
        self._temp_cfg = path
        return path

    def process(self, frame):
        results = self.model.track(
            frame,
            persist=True,
            tracker=self._tracker_cfg,
            classes=[PERSON_CLASS_ID],
            conf=self.config.conf,
            imgsz=self.config.imgsz,
            verbose=False,
        )
        return results[0].boxes

    def close(self):
        if self._temp_cfg and os.path.exists(self._temp_cfg):
            os.remove(self._temp_cfg)
            self._temp_cfg = None