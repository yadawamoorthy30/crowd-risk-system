import time
from typing import Callable, Optional

import cv2

from app.services.video_source import resolve_video_path
from app.services.vision.config import VisionConfig
from app.services.vision.detector import PersonDetector
from app.services.vision.results import FrameResult
from app.services.vision.tracker import TrackManager

PALETTE = [
    (0, 255, 0), (255, 128, 0), (0, 200, 255), (255, 0, 255), (255, 255, 0),
    (0, 128, 255), (180, 105, 255), (0, 255, 160), (255, 80, 80), (80, 255, 255),
]


def open_capture(source: str):
    """Return (capture, label), or (None, reason) if the source cannot be used."""
    if source.isdigit():
        return cv2.VideoCapture(int(source), cv2.CAP_DSHOW), f"webcam {source}"

    path = resolve_video_path(source)
    if not path.is_file():
        return None, f"Video not found: {path}"
    return cv2.VideoCapture(str(path)), f"video {path.name}"


class VideoProcessor:
    def __init__(
        self,
        source: str,
        config: Optional[VisionConfig] = None,
        show_window: bool = False,
        on_result: Optional[Callable[[FrameResult], None]] = None,
    ):
        self.source = source
        self.config = config or VisionConfig()
        self.show_window = show_window
        self.on_result = on_result

        self.detector = PersonDetector(self.config)
        self.tracks = TrackManager()

        self.frames_processed = 0
        self.fps = 0.0
        self.error: Optional[str] = None
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self):
        capture, label = open_capture(self.source)
        if capture is None:
            self.error = label
            return
        if not capture.isOpened():
            self.error = f"Could not open {label}"
            return

        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"Opened {label} ({width}x{height}), tracker: {self.config.tracker}")

        last_time = time.time()
        try:
            while not self._stop_requested:
                success, frame = capture.read()
                if not success:
                    break
                self.frames_processed += 1

                boxes = self.detector.process(frame)
                result = self.tracks.update(boxes, self.frames_processed)

                now = time.time()
                self.fps = 1.0 / max(now - last_time, 1e-6)
                last_time = now

                if self.on_result:
                    self.on_result(result)

                if self.show_window:
                    self._show(frame, result)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
        finally:
            capture.release()
            if self.show_window:
                cv2.destroyAllWindows()

    def _show(self, frame, result: FrameResult):
        for person in result.people:
            color = PALETTE[person.track_id % len(PALETTE)]
            x1, y1 = person.x, person.y
            x2, y2 = x1 + person.width, y1 + person.height

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"ID {person.track_id}  {person.confidence:.2f}",
                        (x1, max(y1 - 5, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            points = self.tracks.trail(person.track_id)
            for p1, p2 in zip(points, points[1:]):
                cv2.line(frame, p1, p2, color, 2)

        cv2.putText(frame,
                    f"Tracked now: {result.people_detected}   Unique IDs so far: {self.tracks.unique_ids}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(frame, f"Frame: {result.frame_number}  FPS: {self.fps:.1f}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        h, w = frame.shape[:2]
        if w > 1280:
            frame = cv2.resize(frame, (1280, int(h * 1280 / w)))
        cv2.imshow("Person tracking (press q to quit)", frame)