import numpy as np

from app.services.vision.heatmap_render import colourise, draw_legend, overlay_heatmap


def hot_norm():
    norm = np.zeros((18, 32), dtype=np.float32)
    norm[9, 16] = 1.0
    return norm


def test_colourise_shapes():
    colour, level = colourise(hot_norm(), 320, 180)
    assert colour.shape == (180, 320, 3)
    assert level.shape == (180, 320)
    assert level.max() > 200


def test_overlay_changes_hot_cells_only():
    frame = np.full((180, 320, 3), 50, dtype=np.uint8)
    out = overlay_heatmap(frame, hot_norm())
    assert out is frame                                   # drawn in place
    assert not np.array_equal(frame[95, 165], [50, 50, 50])
    assert np.array_equal(frame[0, 0], [50, 50, 50])


def test_overlay_all_zero_leaves_frame_unchanged():
    frame = np.full((180, 320, 3), 50, dtype=np.uint8)
    before = frame.copy()
    overlay_heatmap(frame, np.zeros((18, 32), dtype=np.float32))
    assert np.array_equal(frame, before)


def test_legend_draws_on_frame():
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    draw_legend(frame, "Heatmap: last 5 min", "busiest cell: 1.8")
    assert frame.sum() > 0