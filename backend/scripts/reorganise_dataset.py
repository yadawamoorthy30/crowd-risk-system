import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal  # noqa: E402
from app.models.camera import Camera, SourceType  # noqa: E402
from app.services.video_source import PROJECT_ROOT, resolve_video_path  # noqa: E402

DATASET = PROJECT_ROOT / "dataset"

FOLDERS = [
    "raw", "evaluation_clips", "evaluation_clips/validation_tests", "ground_truth",
    "scenarios/steady", "scenarios/rapid_growth", "scenarios/surge", "scenarios/dispersal",
]
KEEP_FOLDERS = ["evaluation_clips", "scenarios/steady", "scenarios/rapid_growth",
                "scenarios/surge", "scenarios/dispersal"]  # get a .gitkeep so Git tracks them

# old path -> new path (both relative to the project root)
MOVES = {
    "dataset/videos/samples/sample_crowd.mp4": "dataset/raw/sample_crowd.mp4",
    "dataset/videos/samples/test_lowres.mp4": "dataset/evaluation_clips/validation_tests/test_lowres.mp4",
    "dataset/videos/samples/test_lowfps.mp4": "dataset/evaluation_clips/validation_tests/test_lowfps.mp4",
    "dataset/videos/samples/test_both.mp4": "dataset/evaluation_clips/validation_tests/test_both.mp4",
    "dataset/videos/samples/test_corrupt.mp4": "dataset/evaluation_clips/validation_tests/test_corrupt.mp4",
}

README = """# Dataset (evaluation only)

The YOLO model is pre-trained. This dataset is used to EVALUATE the system, not to train it:
we compare what the system reports with counts a person made by hand.

| Folder | Contents |
|---|---|
| `raw/` | Full original videos |
| `evaluation_clips/` | Short clips cut from `raw/` that are used for scoring |
| `evaluation_clips/validation_tests/` | Throwaway clips for video-source tests (not in Git) |
| `ground_truth/` | Manual counts, one CSV per clip, named after the clip |
| `scenarios/` | Labelled situations: steady, rapid_growth, surge, dispersal |

## Ground truth format
One CSV per clip (`sample_crowd.mp4` -> `sample_crowd.csv`), see `ground_truth/TEMPLATE.csv`.
Every 5 seconds, count every person visible in the monitored area and write one row:

`time_s,manual_count,zone,notes` - `zone` is `full` for the whole frame, or the zone name.

## Evaluating a clip
1. Register the clip as a camera and run detection on it.
2. Read the stored counts from `GET /api/detection/history/{camera_id}`.
3. For each `time_s` in the CSV, compare `person_count` with `manual_count`.
4. Report the mean absolute error (average of |system - manual|) per clip and per scenario.
"""

SCENARIOS_README = """# Scenarios

| Folder | What N(t) should look like | Used later for |
|---|---|---|
| `steady` | Roughly constant | Checking the system does NOT raise false alarms |
| `rapid_growth` | Climbs quickly over seconds to minutes | Growth-rate and early warning |
| `surge` | Sudden jump (e.g. a gate opens) | Alert latency |
| `dispersal` | Falls steadily | Alerts clearing correctly |

Put clips in the matching folder, or list them in `manifest.csv` if the clip lives in
`evaluation_clips/` and only a time range of it shows the scenario.
"""

TEMPLATES = {
    "README.md": README,
    "scenarios/README.md": SCENARIOS_README,
    "scenarios/manifest.csv": "scenario,clip,start_s,end_s,notes\n",
    "ground_truth/TEMPLATE.csv": "time_s,manual_count,zone,notes\n",
}


def main():
    for folder in FOLDERS:
        (DATASET / folder).mkdir(parents=True, exist_ok=True)
    for folder in KEEP_FOLDERS:
        (DATASET / folder / ".gitkeep").touch()

    for name, text in TEMPLATES.items():
        path = DATASET / name
        if not path.exists():
            path.write_text(text, encoding="utf-8")
            print(f"created {path.relative_to(PROJECT_ROOT)}")

    for old, new in MOVES.items():
        src, dst = PROJECT_ROOT / old, PROJECT_ROOT / new
        if dst.exists():
            print(f"already in place: {new}")
        elif src.exists():
            shutil.move(str(src), str(dst))
            print(f"moved {old} -> {new}")
        else:
            print(f"not found (skipped): {old}")

    # Keep the cameras pointing at the files, so no registered camera breaks
    db = SessionLocal()
    try:
        total = 0
        for old, new in MOVES.items():
            if not resolve_video_path(new).is_file():
                continue
            cameras = (
                db.query(Camera)
                .filter(Camera.source_type == SourceType.FILE, Camera.source_path == old)
                .all()
            )
            for camera in cameras:
                camera.source_path = new
                total += 1
                print(f"camera {camera.id}: source_path -> {new}")
        db.commit()
        print(f"Updated {total} camera(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()