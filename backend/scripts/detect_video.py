import argparse
import time
from pathlib import Path

import cv2
from ultralytics import YOLO

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_VIDEO = PROJECT_ROOT / "dataset" / "videos" / "samples" / "sample_crowd.mp4"
DEFAULT_MODEL = BACKEND_DIR / "models" / "yolo26n.pt"

PERSON_CLASS_ID = 0  # COCO class 0 = person


def parse_args():
    parser = argparse.ArgumentParser(description="Detect people in a video file or webcam")
    parser.add_argument("--source", default=str(DEFAULT_VIDEO),
                        help="video file path, or a webcam index such as 0")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="path to YOLO weights")
    parser.add_argument("--conf", type=float, default=0.35, help="minimum confidence")
    parser.add_argument("--imgsz", type=int, default=640, help="YOLO input size")
    return parser.parse_args()


def open_source(source: str):
    """Return (capture, label), or (None, reason) if the source cannot be used."""
    if source.isdigit():
        index = int(source)
        capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        return capture, f"webcam {index}"

    path = Path(source)
    if not path.is_file():
        return None, f"Video not found: {path}"
    return cv2.VideoCapture(str(path)), f"video {path.name}"


def main():
    args = parse_args()

    capture, label = open_source(args.source)
    if capture is None:
        print(label)
        return
    if not capture.isOpened():
        print(f"Could not open {label}")
        return

    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Opened {label} ({width}x{height})")

    model = YOLO(args.model)

    frame_number = 0
    last_time = time.time()

    while True:
        success, frame = capture.read()
        if not success:
            print("No more frames (end of video, or the camera stopped)")
            break
        frame_number += 1

        results = model.predict(
            frame,
            classes=[PERSON_CLASS_ID],
            conf=args.conf,
            imgsz=args.imgsz,
            verbose=False,
        )
        boxes = results[0].boxes
        people_count = len(boxes)

        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            confidence = float(box.conf[0])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{confidence:.2f}", (x1, max(y1 - 5, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        now = time.time()
        fps = 1.0 / max(now - last_time, 1e-6)
        last_time = now

        cv2.putText(frame, f"People detected: {people_count}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
        cv2.putText(frame, f"Frame: {frame_number}  FPS: {fps:.1f}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        if frame_number % 30 == 0:
            print(f"Frame {frame_number}: {people_count} people")

        # Shrink only the displayed image if it is wider than the screen
        h, w = frame.shape[:2]
        if w > 1280:
            scale = 1280 / w
            frame = cv2.resize(frame, (1280, int(h * scale)))

        cv2.imshow("Person detection (press q to quit)", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    capture.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()