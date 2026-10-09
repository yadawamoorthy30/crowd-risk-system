"""Drawing helpers for the heatmap (OpenCV). The maths lives in heatmap.py."""
import cv2
import numpy as np

ALPHA = 0.45          # how strongly the colours cover the video
MIN_LEVEL = 0.03      # cells below 3% of the peak stay transparent
WHITE = (255, 255, 255)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def colourise(norm: np.ndarray, width: int, height: int):
    """Colour image (BGR, width x height) and its 0-255 level map, from a 0..1 grid.

    Step 8 reuses this to save a heatmap-only picture (no camera frame).
    """
    small = np.clip(norm * 255.0, 0, 255).astype(np.uint8)
    level = cv2.resize(small, (width, height), interpolation=cv2.INTER_LINEAR)
    return cv2.applyColorMap(level, cv2.COLORMAP_JET), level


def overlay_heatmap(frame, norm, alpha: float = ALPHA, min_level: float = MIN_LEVEL):
    """Blend the heatmap into the frame in place; empty cells stay untouched."""
    h, w = frame.shape[:2]
    colour, level = colourise(norm, w, h)
    mask = level > int(min_level * 255)
    if mask.any():
        blended = cv2.addWeighted(frame, 1.0 - alpha, colour, alpha, 0)
        frame[mask] = blended[mask]
    return frame


def _put_right(frame, text: str, y: int, scale: float = 0.6):
    (text_w, _text_h), _ = cv2.getTextSize(text, FONT, scale, 2)
    x = max(frame.shape[1] - text_w - 10, 0)
    cv2.putText(frame, text, (x, y), FONT, scale, WHITE, 2)


def draw_legend(frame, title: str, detail: str):
    """Colour bar (low at the bottom, high at the top) with a title, top right."""
    h, w = frame.shape[:2]
    _put_right(frame, title, 30)
    _put_right(frame, detail, 55)

    bar_w = 24
    x0, y0 = w - bar_w - 20, 75
    bar_h = max(40, min(220, h - y0 - 20))
    gradient = np.linspace(255, 0, bar_h).astype(np.uint8).reshape(-1, 1)
    bar = cv2.applyColorMap(np.repeat(gradient, bar_w, axis=1), cv2.COLORMAP_JET)
    frame[y0:y0 + bar_h, x0:x0 + bar_w] = bar
    cv2.rectangle(frame, (x0 - 1, y0 - 1), (x0 + bar_w, y0 + bar_h), WHITE, 1)
    cv2.putText(frame, "high", (x0 - 50, y0 + 14), FONT, 0.5, WHITE, 1)
    cv2.putText(frame, "low", (x0 - 42, y0 + bar_h), FONT, 0.5, WHITE, 1)
    return frame