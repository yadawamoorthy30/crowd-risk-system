import time
from pathlib import Path

import cv2

from app.models.camera import Camera, SourceType

# backend/app/services/video_source.py -> project root is 3 levels up
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# SRS section 15 recommendations
MIN_WIDTH = 1280
MIN_HEIGHT = 720
MIN_FPS = 10
TEST_FRAMES = 5  # how many frames we try to read


def resolve_video_path(source_path: str) -> Path:
    path = Path(source_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _valid_fps(value) -> bool:
    return value is not None and 1 <= value <= 240  # false for 0, NaN, nonsense


def build_warnings(width: int, height: int, fps) -> list:
    """Pure function: the SRS section 15 rules, easy to test."""
    warnings = []
    if width * height < MIN_WIDTH * MIN_HEIGHT:
        warnings.append(
            f"Resolution {width}x{height} is below the recommended "
            f"{MIN_WIDTH}x{MIN_HEIGHT}; detection accuracy may drop"
        )
    if fps is None:
        warnings.append("Frame rate could not be determined")
    elif fps < MIN_FPS:
        warnings.append(
            f"Frame rate {fps} FPS is below the recommended {MIN_FPS} FPS; "
            "tracking may be unreliable"
        )
    return warnings


def check_source(camera: Camera) -> dict:
    result = {
        "camera_id": camera.id,
        "source_type": camera.source_type.value,
        "source_path": camera.source_path,
        "reachable": False,
        "readable": False,
        "message": "",
        "width": None,
        "height": None,
        "resolution": None,
        "fps": None,
        "frame_count": None,
        "duration_seconds": None,
        "frames_tested": 0,
        "meets_requirements": None,
        "warnings": [],
    }

    # Network streams: opening an unreachable one can hang for a long time,
    # so only the format is validated (already done at registration).
    if camera.source_type in (SourceType.RTSP, SourceType.HTTP):
        result["reachable"] = None
        result["readable"] = None
        result["message"] = "Network stream opening is not tested yet"
        return result

    if camera.source_type == SourceType.FILE:
        path = resolve_video_path(camera.source_path)
        if not path.is_file():
            result["message"] = f"Video file not found: {path}"
            return result
        capture = cv2.VideoCapture(str(path))
    else:  # USB
        capture = cv2.VideoCapture(int(camera.source_path), cv2.CAP_DSHOW)

    try:
        if not capture.isOpened():
            result["message"] = "Source exists but could not be opened"
            return result

        # Read a few frames: one lucky frame does not prove a source is healthy
        frames_ok = 0
        first_frame = None
        t_first = t_last = None
        for _ in range(TEST_FRAMES):
            success, frame = capture.read()
            if not success:
                break
            frames_ok += 1
            t_last = time.perf_counter()
            if first_frame is None:
                first_frame = frame
                t_first = t_last

        result["frames_tested"] = frames_ok
        if frames_ok == 0:
            result["message"] = "Source opened but no frame could be read"
            return result

        result["reachable"] = True
        result["readable"] = True

        # Resolution from a REAL frame: file metadata can be wrong
        height, width = first_frame.shape[:2]
        result["width"], result["height"] = width, height
        result["resolution"] = f"{width}x{height}"

        fps = capture.get(cv2.CAP_PROP_FPS)
        if _valid_fps(fps):
            fps = round(float(fps), 2)
        elif camera.source_type == SourceType.USB and frames_ok > 1 and t_last > t_first:
            fps = round((frames_ok - 1) / (t_last - t_first), 2)  # measured
        else:
            fps = None
        result["fps"] = fps

        if camera.source_type == SourceType.FILE:
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            result["frame_count"] = frame_count
            if fps and frame_count > 0:
                result["duration_seconds"] = round(frame_count / fps, 1)

        warnings = build_warnings(width, height, fps)
        if frames_ok < TEST_FRAMES:
            warnings.append(f"Only {frames_ok} of {TEST_FRAMES} test frames could be read")
        result["warnings"] = warnings
        result["meets_requirements"] = not warnings
        result["message"] = (
            "Source is readable and meets the recommended settings"
            if not warnings
            else f"Source is readable, but with {len(warnings)} warning(s)"
        )
        return result
    finally:
        capture.release()