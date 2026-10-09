"""Run the tracker + tripwire on a clip and show the result in an OpenCV window.

Example (from backend/):
    python scripts\\run_tripwire_clip.py --line 0.1 0.5 0.9 0.5 --in-side RIGHT
"""
import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.vision.config import VisionConfig            # noqa: E402
from app.services.vision.flow import TripwireLine              # noqa: E402
from app.services.vision.video_processor import VideoProcessor  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clip", default=str(
        PROJECT_ROOT / "dataset" / "evaluation_clips" / "tripwire_clip1.mp4"))
    parser.add_argument("--line", nargs=4, type=float, default=[0.1, 0.5, 0.9, 0.5],
                        metavar=("X1", "Y1", "X2", "Y2"))
    parser.add_argument("--in-side", choices=["LEFT", "RIGHT"], default="RIGHT")
    parser.add_argument("--cooldown", type=float, default=3.0)
    parser.add_argument("--initial-count", type=int, default=0)
    parser.add_argument("--flow-window", type=float, default=60.0)
    parser.add_argument("--growth-window", type=float, default=60.0)
    parser.add_argument("--tolerance", type=float, default=30.0)
    parser.add_argument("--min-diff", type=float, default=3.0)
    parser.add_argument("--heatmap-window", type=int, default=5, choices=[1, 5, 15, 30])
    parser.add_argument("--grid", nargs=2, type=int, default=[32, 18], metavar=("COLS", "ROWS"))
    args = parser.parse_args()

    clip = Path(args.clip)
    line = TripwireLine(*args.line, in_side=args.in_side, cooldown_sec=args.cooldown)

    # realtime=False: analyse every Nth frame instead of dropping frames to keep up
    config = VisionConfig(
        realtime=False,
        initial_count=args.initial_count,
        flow_window_sec=args.flow_window,
        growth_window_sec=args.growth_window,
        occupancy_tolerance_pct=args.tolerance,
        occupancy_min_difference=args.min_diff,
        heatmap_cols=args.grid[0],
        heatmap_rows=args.grid[1],
        heatmap_window_min=args.heatmap_window,
    )
    processor = VideoProcessor(str(clip), config=config, show_window=True, tripwire=line)
    processor.run()

    if processor.error:
        print("ERROR:", processor.error)
        return

    flow = processor.flow
    print(f"\nFrames read {processor.frames_read}, processed {processor.frames_processed}")
    print(f"Tripwire result:  IN = {flow.in_total}   OUT = {flow.out_total}")
    for e in flow.events:
        print(f"  {e.video_time:6.1f} s  {e.direction}")

    fm = processor.latest_flow
    if fm is not None and fm.net_flow is not None:
        print(f"Net flow (last {fm.flow_window_sec:g} s): IN {fm.rolling_in}  "
              f"OUT {fm.rolling_out}  net {fm.net_flow:+d}")
        print(f"Cumulative occupancy: {fm.cumulative_occupancy}  (initial {fm.initial_count})")
    if fm is not None:
        rate = "not available" if fm.growth_rate is None else f"{fm.growth_rate:+.1f} people/min"
        print(f"Growth rate R(t) at the end: {rate}  (window {fm.growth_window_sec:g} s)")

    hm = processor.heatmap
    print(f"Heatmap: {hm.cols}x{hm.rows} grid, window {hm.window_minutes} min, busiest cell "
          f"(window) = {hm.peak('window'):.2f} people per frame")

    gt = PROJECT_ROOT / "dataset" / "ground_truth" / f"{clip.stem}.csv"
    if gt.is_file():
        rows = [r.split(",") for r in gt.read_text().splitlines()[1:] if r.strip()]
        gt_in = sum(1 for r in rows if r[1].strip().upper() == "IN")
        gt_out = sum(1 for r in rows if r[1].strip().upper() == "OUT")
        print(f"Ground truth:     IN = {gt_in}   OUT = {gt_out}   ({gt.name})")
    else:
        print(f"(no ground truth file at {gt})")


if __name__ == "__main__":
    main()