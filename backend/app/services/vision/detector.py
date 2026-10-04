from ultralytics import YOLO

from app.services.vision.config import PERSON_CLASS_ID, VisionConfig


class PersonDetector:
    """Loads the YOLO model and runs person detection + tracking on one frame.

    Tracker memory lives inside this object, so use ONE detector per camera.
    """

    def __init__(self, config: VisionConfig):
        self.config = config
        self.model = YOLO(config.model_path)

    def process(self, frame):
        results = self.model.track(
            frame,
            persist=True,
            tracker=self.config.tracker,
            classes=[PERSON_CLASS_ID],
            conf=self.config.conf,
            imgsz=self.config.imgsz,
            verbose=False,
        )
        return results[0].boxes