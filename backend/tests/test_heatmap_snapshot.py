import json
from datetime import datetime

import cv2
import numpy as np
import pytest

from app.services.vision.heatmap import HeatmapCalculator
from app.services.vision.heatmap_render import heatmap_image_size, render_heatmap_image
from app.services.vision.heatmap_snapshot import (
    build_image_path, heatmap_fields, render_snapshot_png,
)

W, H = 320, 180
TS = datetime(2026, 10, 10, 12, 30, 45, 123000)


def make_calc():
    calc = HeatmapCalculator(32, 18, 5)
    calc.update([(165, 95)], W, H, 0.0)
    calc.update([(165, 95)], W, H, 1.0)
    return calc


def test_fields_window_mode():
    f = heatmap_fields(make_calc(), "window", TS)
    assert f["mode"] == "WINDOW"
    assert f["window_sec"] == 300
    assert (f["grid_cols"], f["grid_rows"]) == (32, 18)
    assert len(f["grid_data"]) == 18 and len(f["grid_data"][0]) == 32
    assert f["grid_data"][9][16] == 1.0


def test_fields_instant_mode():
    f = heatmap_fields(make_calc(), "instant", TS)
    assert f["mode"] == "INSTANT"
    assert f["window_sec"] is None
    assert f["grid_data"][9][16] == 1.0


def test_fields_reject_unknown_mode():
    with pytest.raises(ValueError):
        heatmap_fields(make_calc(), "bogus", TS)


def test_fields_grid_is_json_serialisable():
    assert json.dumps(heatmap_fields(make_calc(), "window", TS)["grid_data"])


def test_fields_contain_only_aggregated_columns():
    # privacy rule: no track ids, boxes or positions
    assert set(heatmap_fields(make_calc(), "window", TS)) == {
        "ts", "mode", "window_sec", "grid_cols", "grid_rows", "grid_data",
    }


def test_build_image_path():
    assert build_image_path(19, TS, "window") == \
        "heatmaps/camera_19/20261010_123045_123_window.png"


def test_image_size_keeps_aspect_ratio():
    assert heatmap_image_size(1280, 720) == (640, 360)


def test_image_size_portrait_and_invalid():
    assert heatmap_image_size(720, 1280) == (640, 1138)
    assert heatmap_image_size(0, 0) == (640, 360)


def test_image_has_no_camera_frame_only_legend_and_heat():
    # an empty heatmap: everything is black except the small legend at the top right
    image = render_heatmap_image(np.zeros((18, 32), dtype=np.float32), 640, 360, "T", "d")
    assert image[:, :500].sum() == 0
    assert image.sum() > 0


def test_image_colours_the_hot_cell():
    norm = np.zeros((18, 32), dtype=np.float32)
    norm[9, 16] = 1.0
    image = render_heatmap_image(norm, 640, 360, "T", "d")
    assert image[190, 330].any()


def test_snapshot_png_decodes_to_the_expected_size():
    png = render_snapshot_png(make_calc(), "window", 1280, 720)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    decoded = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape == (360, 640, 3)