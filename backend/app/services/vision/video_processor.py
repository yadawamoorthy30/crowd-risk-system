import time
from collections import deque
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


def fit_to_processing_size(frame, max_w: int, max_h: int):
    """Scale DOWN to fit inside max_w x max_h, keeping the aspect ratio."""
    h, w = frame.shape[:2]
    scale = min(max_w / w, max_h / h, 1.0)  # 1.0 = never upscale
    if scale < 1.0:
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)),
                           interpolation=cv2.INTER_AREA)
    return frame


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
        self.tracks = TrackManager(
            history_length=self.config.history_length,
            track_buffer=self.config.track_buffer,
        )

        self.frames_read = 0        # every frame taken from the source
        self.frames_processed = 0   # frames actually analysed
        self.frames_skipped = 0
        self.frame_width = 0        # size of the processed frame
        self.frame_height = 0
        self.source_fps = 0.0
        self.error: Optional[str] = None
        self._stamps = deque(maxlen=30)  # finish times of recent processed frames
        self._stop_requested = False

    @property
    def fps(self) -> float:
        """Measured processing FPS over the last 30 processed frames."""
        if len(self._stamps) < 2:
            return 0.0
        span = self._stamps[-1] - self._stamps[0]
        return (len(self._stamps) - 1) / span if span > 0 else 0.0

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

        try:
            self._loop(capture, label)
        finally:
            capture.release()
            self.detector.close()
            if self.show_window:
                cv2.destroyAllWindows()

    def _loop(self, capture, label: str):
        source_fps = capture.get(cv2.CAP_PROP_FPS)
        if not (1 <= source_fps <= 240):  # 0, NaN or nonsense -> assume 30
            source_fps = 30.0
        self.source_fps = source_fps

        stride = max(1, round(source_fps / max(self.config.target_fps, 1)))
        print(f"Opened {label}, source {source_fps:.1f} fps -> analysing every "
              f"{stride} frame(s) (target {self.config.target_fps} fps), "
              f"max size {self.config.process_width}x{self.config.process_height}, "
              f"conf {self.config.conf}, track_buffer {self.config.track_buffer}, "
              f"realtime={self.config.realtime}")

        skip_pending = 0
        while not self._stop_requested:
            if not capture.grab():          # cheap: advances without full decode/convert
                break
            self.frames_read += 1

            if skip_pending > 0:
                skip_pending -= 1
                self.frames_skipped += 1
                continue

            success, frame = capture.retrieve()
            if not success:
                break

            started = time.perf_counter()
            frame = fit_to_processing_size(
                frame, self.config.process_width, self.config.process_height
            )
            self.frame_height, self.frame_width = frame.shape[:2]

            boxes = self.detector.process(frame)
            result = self.tracks.update(
                boxes, self.frames_read, self.frame_width, self.frame_height
            )
            self.frames_processed += 1

            finished = time.perf_counter()
            self._stamps.append(finished)

            # frames to skip before the next analysis
            skip_pending = stride - 1
            if self.config.realtime:
                behind = round((finished - started) * source_fps)  # frames that passed meanwhile
                skip_pending = max(stride, behind) - 1

            if self.on_result:
                self.on_result(result)

            if self.show_window:
                self._show(frame, result)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    def _show(self, frame, result: FrameResult):
        for person in result.people:
            color = PALETTE[person.track_id % len(PALETTE)]
            x1, y1 = person.x, person.y
            x2, y2 = x1 + person.width, y1 + person.height

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.circle(frame, (person.foot_x, person.foot_y), 4, color, -1)  # foot point
            cv2.putText(frame, f"ID {person.track_id}  {person.confidence:.2f}",
                        (x1, max(y1 - 5, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            points = self.tracks.trail(person.track_id)
            for p1, p2 in zip(points, points[1:]):
                cv2.line(frame, p1, p2, color, 2)

        cv2.putText(frame,
                    f"Tracked now: {result.people_detected}   Unique IDs so far: {self.tracks.unique_ids}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(frame,
                    f"Frame: {result.frame_number}  FPS: {self.fps:.1f}/{self.config.target_fps}  "
                    f"Skipped: {self.frames_skipped}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.imshow("Person tracking (press q to quit)", frame)