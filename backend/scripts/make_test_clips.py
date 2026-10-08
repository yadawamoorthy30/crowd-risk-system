import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.video_source import resolve_video_path  # noqa: E402

SOURCE = "dataset/raw/sample_crowd.mp4"
OUT_DIR = resolve_video_path("dataset/evaluation_clips/validation_tests")
FRAMES = 40


def make_clip(name: str, size: tuple, fps: int):
    capture = cv2.VideoCapture(str(resolve_video_path(SOURCE)))
    writer = cv2.VideoWriter(str(OUT_DIR / name), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    for _ in range(FRAMES):
        success, frame = capture.read()
        if not success:
            break
        writer.write(cv2.resize(frame, size))
    writer.release()
    capture.release()
    print(f"created {name}: {size[0]}x{size[1]} @ {fps} fps")


make_clip("test_lowres.mp4", (640, 360), 15)     # resolution warning only
make_clip("test_lowfps.mp4", (1280, 720), 5)     # FPS warning only
make_clip("test_both.mp4", (640, 360), 5)        # both warnings
(OUT_DIR / "test_corrupt.mp4").write_text("this is not a video")
print("created test_corrupt.mp4 (not a real video)")