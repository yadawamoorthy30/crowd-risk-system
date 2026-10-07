from pathlib import Path

import cv2

from app.models.camera import Camera, SourceType

# backend/app/services/video_source.py -> project root is 3 levels up
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def resolve_video_path(source_path: str) -> Path:
    path = Path(source_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def check_source(camera: Camera) -> dict:
    result = {
        "camera_id": camera.id,
        "source_type": camera.source_type.value,
        "source_path": camera.source_path,
        "reachable": False,
        "message": "",
        "width": None,
        "height": None,
        "fps": None,
        "frame_count": None,
    }

    # RTSP: opening an unreachable stream can hang for a long time,
    # so Phase 1 only validates the format (already done at registration).
    if camera.source_type in (SourceType.RTSP, SourceType.HTTP):
        result["reachable"] = None
        result["message"] = "Network stream opening is not tested yet"
        return result

    if camera.source_type == SourceType.FILE:
        path = resolve_video_path(camera.source_path)
        if not path.is_file():
            result["message"] = f"Video file not found: {path}"
            return result
        capture = cv2.VideoCapture(str(path))
    else:  # webcam
        capture = cv2.VideoCapture(int(camera.source_path), cv2.CAP_DSHOW)

    try:
        if not capture.isOpened():
            result["message"] = "Source exists but could not be opened"
            return result

        success, _frame = capture.read()
        if not success:
            result["message"] = "Source opened but no frame could be read"
            return result

        result["reachable"] = True
        result["message"] = "Source opened and a frame was read successfully"
        result["width"] = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        result["height"] = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        result["fps"] = round(capture.get(cv2.CAP_PROP_FPS), 2)
        if camera.source_type == SourceType.FILE:
            result["frame_count"] = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        return result
    finally:
        capture.release()