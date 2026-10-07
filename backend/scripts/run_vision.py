import argparse
import csv
import sys
from pathlib import Path

# Let this script find the "app" package (it lives one folder up)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.vision.config import VisionConfig  # noqa: E402
from app.services.vision.results import FrameResult  # noqa: E402
from app.services.vision.video_processor import VideoProcessor  # noqa: E402

DEFAULT_SOURCE = "dataset/videos/samples/sample_crowd.mp4"


def parse_args():
    parser = argparse.ArgumentParser(description="Run the vision service on a video or webcam")
    parser.add_argument("--source", default=DEFAULT_SOURCE,
                        help="video path (relative to the project root) or a webcam index such as 0")
    parser.add_argument("--tracker", default="bytetrack.yaml", help="bytetrack.yaml or botsort.yaml")
    parser.add_argument("--conf", type=float, default=0.40, help="minimum detection confidence")
    parser.add_argument("--imgsz", type=int, default=640, help="YOLO input size")
    parser.add_argument("--fps", type=int, default=10, help="target analysis rate")
    parser.add_argument("--track-buffer", type=int, default=30, help="frames a lost track is kept")
    parser.add_argument("--realtime", action="store_true", help="drop frames when falling behind")
    parser.add_argument("--csv", default=None, help="optional path to save tracking results")
    return parser.parse_args()


def main():
    args = parse_args()
    config = VisionConfig(
        tracker=args.tracker, conf=args.conf, imgsz=args.imgsz,
        target_fps=args.fps, track_buffer=args.track_buffer, realtime=args.realtime,
    )

    csv_file = None
    writer = None
    if args.csv:
        csv_path = Path(args.csv)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        csv_file = open(csv_path, "w", newline="")
        writer = csv.writer(csv_file)
        writer.writerow(["frame_number", "timestamp", "track_id", "confidence",
                         "x", "y", "width", "height", "foot_x", "foot_y"])

    def on_result(result: FrameResult):
        if result.frame_number % 30 == 0:
            print(f"Frame {result.frame_number}: {result.people_detected} tracked")
        if writer:
            for p in result.people:
                writer.writerow([result.frame_number,
                                 result.timestamp.isoformat(timespec="milliseconds"),
                                 p.track_id, p.confidence, p.x, p.y, p.width, p.height,
                                 p.foot_x, p.foot_y])

    processor = VideoProcessor(args.source, config=config, show_window=True, on_result=on_result)
    try:
        processor.run()
    finally:
        if csv_file:
            csv_file.close()

    if processor.error:
        print(f"Error: {processor.error}")
    print(f"Done. Read: {processor.frames_read}, analysed: {processor.frames_processed}, "
          f"skipped: {processor.frames_skipped}, unique track IDs: {processor.tracks.unique_ids}, "
          f"still in memory: {processor.tracks.tracks_in_memory}")


if __name__ == "__main__":
    main()