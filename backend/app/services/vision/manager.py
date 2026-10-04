import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from app.services.vision import persistence
from app.services.vision.config import SNAPSHOT_INTERVAL_SECONDS, VisionConfig
from app.services.vision.results import FrameResult
from app.services.vision.video_processor import VideoProcessor


class SessionAlreadyRunning(Exception):
    pass


@dataclass
class DetectionSession:
    camera_id: int
    source: str
    started_at: datetime
    run_id: Optional[int] = None
    processor: Optional[VideoProcessor] = None
    state: str = "running"          # running | stopped | finished | error
    error: Optional[str] = None
    stop_requested: bool = False
    latest: Optional[FrameResult] = None
    thread: Optional[threading.Thread] = None
    last_saved_at: float = 0.0
    snapshots_saved: int = 0
    db_errors: int = 0


class DetectionManager:
    def __init__(self):
        self._sessions: Dict[int, DetectionSession] = {}
        self._lock = threading.Lock()

    def start(self, camera_id: int, source: str, config: VisionConfig) -> DetectionSession:
        with self._lock:
            existing = self._sessions.get(camera_id)
            if existing and existing.thread and existing.thread.is_alive():
                raise SessionAlreadyRunning(f"Detection is already running for camera {camera_id}")

            session = DetectionSession(camera_id=camera_id, source=source, started_at=datetime.now())

            def on_result(result: FrameResult):
                session.latest = result  # always keep the newest result in memory

                now = time.monotonic()
                if now - session.last_saved_at >= SNAPSHOT_INTERVAL_SECONDS:
                    session.last_saved_at = now
                    try:
                        persistence.save_snapshot(session.run_id, result)
                        session.snapshots_saved += 1
                    except Exception as error:
                        session.db_errors += 1
                        print(f"Could not save snapshot for run {session.run_id}: {error}")

            # Build the detector first: a missing model fails here, before any run row exists
            session.processor = VideoProcessor(
                source, config=config, show_window=False, on_result=on_result
            )
            session.run_id = persistence.create_run(camera_id, config)

            session.thread = threading.Thread(
                target=self._run, args=(session,), daemon=True,
                name=f"detection-camera-{camera_id}",
            )
            self._sessions[camera_id] = session
            session.thread.start()
            return session

    def _run(self, session: DetectionSession):
        try:
            session.processor.run()
            if session.processor.error:
                session.state = "error"
                session.error = session.processor.error
            elif session.stop_requested:
                session.state = "stopped"
            else:
                session.state = "finished"   # the video simply ended
        except Exception as error:
            session.state = "error"
            session.error = str(error)
        finally:
            try:
                persistence.finish_run(
                    session.run_id, session.state,
                    session.processor.frames_processed, session.error,
                )
            except Exception as error:
                print(f"Could not close run {session.run_id}: {error}")

    def stop(self, camera_id: int) -> Optional[DetectionSession]:
        session = self._sessions.get(camera_id)
        if session is None:
            return None
        if session.thread and session.thread.is_alive():
            session.stop_requested = True
            session.processor.stop()
            session.thread.join(timeout=10)
        return session

    def get(self, camera_id: int) -> Optional[DetectionSession]:
        return self._sessions.get(camera_id)

    def sessions(self, camera_id: Optional[int] = None) -> List[DetectionSession]:
        items = list(self._sessions.values())
        if camera_id is not None:
            items = [s for s in items if s.camera_id == camera_id]
        return sorted(items, key=lambda s: s.camera_id)


# One shared manager for the whole application
detection_manager = DetectionManager()