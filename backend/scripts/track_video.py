import argparse
import csv
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

import cv2
from ultralytics import YOLO

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_VIDEO = PROJECT_ROOT / "dataset" / "videos" / "samples" / "sample_crowd.mp4"
DEFAULT_MODEL = BACKEND_DIR / "models" / "yolo26n.pt"

PERSON_CLASS_ID = 0  # COCO class 0 = person

# One colour per ID (BGR), reused cyclically
PALETTE = [
    (0, 255, 0), (255, 128, 0), (0, 200, 255), (255, 0, 255), (255, 255, 0),
    (0, 128, 255), (180, 105, 255), (0, 255, 160), (255, 80, 80), (80, 255, 255),
]


def parse_args():
    parser = argparse.ArgumentParser(description="Detect and track people")
    parser.add_argument("--source", default=str(DEFAULT_VIDEO),
                        help="video file path, or a webcam index such as 0")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="path to YOLO weights")
    parser.add_argument("--tracker", default="bytetrack.yaml",
                        help="bytetrack.yaml or botsort.yaml")
    parser.add_argument("--conf", type=float, default=0.25, help="minimum detection confidence")
    parser.add_argument("--imgsz", type=int, default=640, help="YOLO input size")
    parser.add_argument("--csv", default=None, help="optional path to save tracking results")
    return parser.parse_args()


def open_source(source: str):
    """Return (capture, label), or (None, reason) if the source cannot be used."""
    if source.isdigit():
        index = int(source)
        return cv2.VideoCapture(index, cv2.CAP_DSHOW), f"webcam {index}"

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
    print(f"Opened {label} ({width}x{height}), tracker: {args.tracker}")

    model = YOLO(args.model)

    csv_file = None
    writer = None
    if args.csv:
        csv_path = Path(args.csv)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        csv_file = open(csv_path, "w", newline="")
        writer = csv.writer(csv_file)
        writer.writerow(["frame_number", "timestamp", "track_id",
                         "confidence", "x", "y", "width", "height"])

    trails = defaultdict(lambda: deque(maxlen=30))
    seen_ids = set()
    frame_number = 0
    last_time = time.time()

    while True:
        success, frame = capture.read()
        if not success:
            print("No more frames (end of video, or the camera stopped)")
            break
        frame_number += 1
        timestamp = datetime.now().isoformat(timespec="milliseconds")

        results = model.track(
            frame,
            persist=True,
            tracker=args.tracker,
            classes=[PERSON_CLASS_ID],
            conf=args.conf,
            imgsz=args.imgsz,
            verbose=False,
        )
        boxes = results[0].boxes

        tracked_now = 0
        if boxes.id is not None:
            track_ids = boxes.id.int().tolist()
            for box, track_id in zip(boxes, track_ids):
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                confidence = float(box.conf[0])
                color = PALETTE[track_id % len(PALETTE)]

                tracked_now += 1
                seen_ids.add(track_id)
                trails[track_id].append(((x1 + x2) // 2, y2))  # bottom-centre point

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"ID {track_id}  {confidence:.2f}", (x1, max(y1 - 5, 15)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                points = list(trails[track_id])
                for p1, p2 in zip(points, points[1:]):
                    cv2.line(frame, p1, p2, color, 2)

                if writer:
                    writer.writerow([frame_number, timestamp, track_id,
                                     round(confidence, 3), x1, y1, x2 - x1, y2 - y1])

        now = time.time()
        fps = 1.0 / max(now - last_time, 1e-6)
        last_time = now

        cv2.putText(frame, f"Tracked now: {tracked_now}   Unique IDs so far: {len(seen_ids)}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(frame, f"Frame: {frame_number}  FPS: {fps:.1f}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        if frame_number % 30 == 0:
            print(f"Frame {frame_number}: {tracked_now} tracked, {len(seen_ids)} unique IDs so far")

        h, w = frame.shape[:2]
        if w > 1280:
            scale = 1280 / w
            frame = cv2.resize(frame, (1280, int(h * scale)))

        cv2.imshow("Person tracking (press q to quit)", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    capture.release()
    cv2.destroyAllWindows()
    if csv_file:
        csv_file.close()
        print(f"Saved results to {args.csv}")
    print(f"Done. Frames processed: {frame_number}, unique track IDs: {len(seen_ids)}")


if __name__ == "__main__":
    main()