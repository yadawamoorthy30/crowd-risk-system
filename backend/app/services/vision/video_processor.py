import time
from collections import deque
from typing import Callable, Optional
import numpy as np
import cv2

from app.services.video_source import resolve_video_path
from app.services.vision.config import VisionConfig
from app.services.vision.detector import PersonDetector
from app.services.vision.results import FrameResult
from app.services.vision.tracker import TrackManager
from app.services.vision.metrics import MetricsCalculator, MonitorArea
from app.services.vision.flow import TripwireCounter, TripwireLine
from app.services.vision.flow_metrics import FlowMetricsCalculator

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
        monitor: Optional[MonitorArea] = None,
        tripwire: Optional[TripwireLine] = None,
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
        self.metrics = MetricsCalculator(monitor or MonitorArea(), self.config.smoothing_seconds)

                # Tripwire IN/OUT counting (None = no tripwire configured)
        self.flow = (
            TripwireCounter(tripwire, forget_after=self.config.track_buffer)
            if tripwire is not None else None
        )

        # F(t), cumulative occupancy and R(t); growth works even without a tripwire
        self.flow_calc = FlowMetricsCalculator(
            initial_count=self.config.initial_count,
            flow_window_sec=self.config.flow_window_sec,
            growth_window_sec=self.config.growth_window_sec,
        )
        self.latest_flow = None

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
            result.metrics = self.metrics.update(
                result.people, self.frame_width, self.frame_height
            )

            video_time = self.frames_read / self.source_fps   # seconds into the video
            if self.flow is not None:
                self.flow.update(
                    result.people, self.frame_width, self.frame_height, video_time
                )
            result.flow = self.latest_flow = self.flow_calc.update(
                self.flow, result.metrics.people_count_smoothed, video_time
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
        h, w = frame.shape[:2]
        monitor = self.metrics.monitor
        m = result.metrics

        if monitor.mode == "zone" and monitor.polygon:
            pts = np.array([[int(x * w), int(y * h)] for x, y in monitor.polygon], np.int32)
            cv2.polylines(frame, [pts], True, (0, 255, 255), 2)

        for person in result.people:
            # people outside the zone are drawn grey: tracked, but not counted
            color = PALETTE[person.track_id % len(PALETTE)] if person.counted else (128, 128, 128)
            x1, y1 = person.x, person.y
            x2, y2 = x1 + person.width, y1 + person.height

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.circle(frame, (person.foot_x, person.foot_y), 4, color, -1)
            cv2.putText(frame, f"ID {person.track_id}  {person.confidence:.2f}",
                        (x1, max(y1 - 5, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            points = self.tracks.trail(person.track_id)
            for p1, p2 in zip(points, points[1:]):
                cv2.line(frame, p1, p2, color, 2)

        if self.flow is not None:
            self._draw_tripwire(frame)
        self._draw_flow_metrics(frame)

        yellow = (0, 255, 255)
        cv2.putText(frame, f"Tracked in frame: {result.people_detected}   "
                           f"Unique IDs so far: {self.tracks.unique_ids}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, yellow, 2)
        cv2.putText(frame, f"N(t): {m.people_count}  (avg {m.people_count_smoothed:.1f})",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, yellow, 2)
        if m.density is None:
            density_text = f"D(t): {m.message}"
        else:
            density_text = f"D(t): {m.density:.3f}  (avg {m.density_smoothed:.3f}) people/m2"
        cv2.putText(frame, density_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, yellow, 2)

        area_text = f"{m.area_sqm:g} m2" if m.area_sqm is not None else "area not set"
        label = f"Zone: {m.zone_name} ({area_text})" if m.mode == "zone" else f"Full frame ({area_text})"
        cv2.putText(frame, label, (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, yellow, 2)
        cv2.putText(frame, f"Frame: {result.frame_number}  FPS: {self.fps:.1f}/{self.config.target_fps}  "
                           f"Skipped: {self.frames_skipped}",
                    (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, yellow, 2)
        cv2.imshow("Person tracking (press q to quit)", frame)


    def _draw_tripwire(self, frame):
        h, w = frame.shape[:2]
        line = self.flow.line
        ax, ay = int(line.x1 * w), int(line.y1 * h)
        bx, by = int(line.x2 * w), int(line.y2 * h)
        red = (0, 0, 255)
        cv2.line(frame, (ax, ay), (bx, by), red, 3)

        # arrow pointing to the IN side
        dx, dy = bx - ax, by - ay
        length = max((dx * dx + dy * dy) ** 0.5, 1.0)
        nx, ny = -dy / length, dx / length       # unit normal towards the RIGHT side
        mx, my = (ax + bx) // 2, (ay + by) // 2
        tip = (int(mx + line.in_sign * nx * 50), int(my + line.in_sign * ny * 50))
        cv2.arrowedLine(frame, (mx, my), tip, red, 3, tipLength=0.3)
        cv2.putText(frame, "IN", (tip[0] + 6, tip[1] + 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, red, 2)

        cv2.putText(frame, f"IN: {self.flow.in_total}   OUT: {self.flow.out_total}",
                    (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.9, red, 2)
        
    def _draw_flow_metrics(self, frame):
        fm = self.latest_flow
        if fm is None:
            return
        green = (0, 255, 0)
        y = 210
        if fm.net_flow is not None:
            cv2.putText(frame, f"F(t) last {fm.flow_window_sec:g}s: IN {fm.rolling_in}  "
                               f"OUT {fm.rolling_out}  net {fm.net_flow:+d}",
                        (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, green, 2)
            y += 30
            cv2.putText(frame, f"Occupancy: {fm.cumulative_occupancy}  (start {fm.initial_count})",
                        (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, green, 2)
            y += 30
        if fm.growth_rate is None:
            growth_text = "R(t): warming up"
        else:
            growth_text = f"R(t): {fm.growth_rate:+.1f} people/min  (over {fm.growth_window_sec:g}s)"
        cv2.putText(frame, growth_text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, green, 2)

        