"""Pick a tripwire by clicking on a frame of a clip.
(Admin helper until the Phase 4 dashboard has a drawing screen.)

Run from backend/:
    python scripts\\pick_tripwire.py --clip ..\\dataset\\evaluation_clips\\tripwire_clip1.mp4
    python scripts\\pick_tripwire.py --clip ... --camera-id 1     (enables saving with 's')

Mouse: click point 1, click point 2 (a third click starts over).
Keys:  f = flip IN side    r = reset    s = save to API    q = quit
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import cv2

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.tripwire import MIN_LENGTH_FRAC, line_length_in_frame_widths  # noqa: E402

WINDOW = "Pick tripwire"
RED = (0, 0, 255)
GREEN = (0, 200, 0)
YELLOW = (0, 255, 255)


def grab_frame(clip: Path, seconds: float):
    capture = cv2.VideoCapture(str(clip))
    if not capture.isOpened():
        return None
    capture.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
    ok, frame = capture.read()
    capture.release()
    if not ok:
        return None
    h, w = frame.shape[:2]
    scale = min(1280 / w, 720 / h, 1.0)          # same size rule as the processor
    if scale < 1.0:
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)),
                           interpolation=cv2.INTER_AREA)
    return frame


def build_body(points, size, in_side, cooldown):
    (x1, y1), (x2, y2) = points
    w, h = size
    return {
        "x1": round(x1 / w, 5), "y1": round(y1 / h, 5),
        "x2": round(x2 / w, 5), "y2": round(y2 / h, 5),
        "in_side": in_side, "cooldown_sec": cooldown,
    }


def save_to_api(api: str, camera_id: int, body: dict):
    request = urllib.request.Request(
        f"{api}/api/cameras/{camera_id}/tripwire",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            print(f"SAVED (HTTP {response.status}):", response.read().decode())
    except urllib.error.HTTPError as error:
        print(f"REJECTED (HTTP {error.code}):", error.read().decode())
    except urllib.error.URLError as error:
        print("Could not reach the API. Is uvicorn running?", error.reason)


def draw(frame, points, in_side):
    canvas = frame.copy()
    h, w = canvas.shape[:2]
    for p in points:
        cv2.circle(canvas, p, 6, RED, -1)

    status = "Click point 1, then point 2"
    if len(points) == 2:
        (ax, ay), (bx, by) = points
        body = build_body(points, (w, h), in_side, 3)
        length = line_length_in_frame_widths(body["x1"], body["y1"], body["x2"], body["y2"])
        ok = length >= MIN_LENGTH_FRAC - 1e-9
        color = RED if ok else (0, 128, 255)
        cv2.line(canvas, (ax, ay), (bx, by), color, 3)

        # arrow towards the IN side (same maths as the processor)
        dx, dy = bx - ax, by - ay
        norm = max((dx * dx + dy * dy) ** 0.5, 1.0)
        sign = 1 if in_side == "RIGHT" else -1
        mx, my = (ax + bx) // 2, (ay + by) // 2
        tip = (int(mx + sign * (-dy / norm) * 50), int(my + sign * (dx / norm) * 50))
        cv2.arrowedLine(canvas, (mx, my), tip, color, 3, tipLength=0.3)
        cv2.putText(canvas, "IN", (tip[0] + 6, tip[1] + 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        status = (f"Length {length * 100:.0f}% of width "
                  f"({'OK' if ok else 'TOO SHORT, min 20%'})   IN side: {in_side}")

    cv2.putText(canvas, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, YELLOW, 2)
    cv2.putText(canvas, "click=point  f=flip IN side  r=reset  s=save  q=quit",
                (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, YELLOW, 2)
    return canvas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clip", required=True)
    parser.add_argument("--at", type=float, default=1.0, help="second of the clip to use as snapshot")
    parser.add_argument("--camera-id", type=int, help="enables saving to the API")
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--in-side", choices=["LEFT", "RIGHT"], default="RIGHT")
    parser.add_argument("--cooldown", type=int, default=3)
    args = parser.parse_args()

    frame = grab_frame(Path(args.clip), args.at)
    if frame is None:
        print("Could not read a frame. Check --clip and --at (must be inside the clip).")
        return

    h, w = frame.shape[:2]
    points = []
    in_side = args.in_side

    def on_mouse(event, x, y, _flags, _param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(points) >= 2:
                points.clear()
            points.append((x, y))

    cv2.namedWindow(WINDOW)
    cv2.setMouseCallback(WINDOW, on_mouse)

    while True:
        cv2.imshow(WINDOW, draw(frame, points, in_side))
        key = cv2.waitKey(30) & 0xFF
        if key == ord("q"):
            break
        if key == ord("r"):
            points.clear()
        elif key == ord("f"):
            in_side = "LEFT" if in_side == "RIGHT" else "RIGHT"
        elif key == ord("s"):
            if len(points) != 2:
                print("Place both points first.")
            elif args.camera_id is None:
                print("Start the script with --camera-id N to enable saving.")
            else:
                save_to_api(args.api, args.camera_id,
                            build_body(points, (w, h), in_side, args.cooldown))
    cv2.destroyAllWindows()

    if len(points) == 2:
        body = build_body(points, (w, h), in_side, args.cooldown)
        print("\nRequest body for PUT /api/cameras/{id}/tripwire:")
        print(json.dumps(body, indent=2))
        print("\nTo test the line on the clip:")
        print(f"python scripts\\run_tripwire_clip.py --clip \"{args.clip}\" "
              f"--line {body['x1']} {body['y1']} {body['x2']} {body['y2']} "
              f"--in-side {in_side} --cooldown {args.cooldown}")


if __name__ == "__main__":
    main()