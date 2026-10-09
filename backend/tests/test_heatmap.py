import numpy as np
import pytest

from app.services.vision.heatmap import (
    HeatmapCalculator, WindowAccumulator, cell_index, instant_grid,
    normalise, window_seconds,
)

W, H, COLS, ROWS = 320, 180, 32, 18      # every cell is 10 x 10 pixels


def grid_with(row, col, value):
    grid = np.zeros((ROWS, COLS), dtype=np.int32)
    grid[row, col] = value
    return grid


# ---------- cell mapping ----------

def test_cell_index_known_cell():
    assert cell_index(165, 95, W, H, COLS, ROWS) == (9, 16)


def test_cell_index_corners():
    assert cell_index(0, 0, W, H, COLS, ROWS) == (0, 0)
    assert cell_index(W, H, W, H, COLS, ROWS) == (ROWS - 1, COLS - 1)


def test_cell_index_outside_frame_is_none():
    assert cell_index(-1, 50, W, H, COLS, ROWS) is None
    assert cell_index(50, H + 1, W, H, COLS, ROWS) is None
    assert cell_index(W + 1, 50, W, H, COLS, ROWS) is None


def test_cell_index_bad_frame_size():
    assert cell_index(10, 10, 0, 0, COLS, ROWS) is None


def test_instant_grid_counts_people_per_cell():
    grid = instant_grid([(165, 95), (168, 99), (5, 5)], W, H, COLS, ROWS)
    assert grid.shape == (ROWS, COLS)
    assert grid[9, 16] == 2
    assert grid[0, 0] == 1
    assert grid.sum() == 3


def test_instant_grid_ignores_points_outside():
    assert instant_grid([(-5, 10), (50, 500)], W, H, COLS, ROWS).sum() == 0


def test_normalise_scales_to_peak():
    grid = np.zeros((ROWS, COLS), dtype=np.int32)
    grid[0, 0], grid[1, 1] = 4, 2
    norm = normalise(grid)
    assert norm[0, 0] == 1.0
    assert norm[1, 1] == 0.5


def test_normalise_all_zero():
    assert normalise(np.zeros((ROWS, COLS), dtype=np.int32)).max() == 0.0


# ---------- window options ----------

def test_window_seconds_allowed_values():
    assert [window_seconds(m) for m in (1, 5, 15, 30)] == [60.0, 300.0, 900.0, 1800.0]


def test_window_seconds_rejects_other_values():
    with pytest.raises(ValueError):
        window_seconds(7)


# ---------- accumulation and expiry ----------

def test_accumulator_average_per_frame():
    acc = WindowAccumulator(COLS, ROWS, 60)
    acc.add(grid_with(2, 3, 1), 0.0)
    acc.add(grid_with(2, 3, 3), 0.5)
    assert acc.mean_grid()[2, 3] == pytest.approx(2.0)
    assert acc.frames == 2


def test_accumulator_empty_is_zero():
    acc = WindowAccumulator(COLS, ROWS, 60)
    assert acc.mean_grid().sum() == 0
    assert acc.frames == 0


def test_accumulator_expires_old_frames():
    acc = WindowAccumulator(COLS, ROWS, 60)
    acc.add(grid_with(0, 0, 5), 0.0)
    acc.add(grid_with(1, 1, 1), 61.0)
    mean = acc.mean_grid()
    assert mean[0, 0] == 0
    assert mean[1, 1] == pytest.approx(1.0)
    assert acc.frames == 1


def test_accumulator_keeps_frames_inside_window():
    acc = WindowAccumulator(COLS, ROWS, 60)
    acc.add(grid_with(0, 0, 2), 0.0)
    acc.add(grid_with(0, 0, 4), 30.0)
    assert acc.mean_grid()[0, 0] == pytest.approx(3.0)
    assert acc.frames == 2


def test_accumulator_merges_frames_in_the_same_second():
    acc = WindowAccumulator(COLS, ROWS, 60)
    for i in range(3):
        acc.add(grid_with(0, 0, 1), 5.0 + i * 0.2)
    assert acc.buckets == 1
    assert acc.frames == 3


def test_accumulator_memory_is_bounded():
    acc = WindowAccumulator(COLS, ROWS, 60)
    for i in range(2000):                       # 200 s at 10 frames per second
        acc.add(grid_with(0, 0, 1), i * 0.1)
    assert acc.buckets <= 62


# ---------- calculator ----------

def test_calculator_instant_and_window():
    calc = HeatmapCalculator(COLS, ROWS, 5)
    calc.update([(165, 95)], W, H, 0.0)
    calc.update([(165, 95), (168, 99)], W, H, 1.0)
    assert calc.grid("instant")[9, 16] == 2
    assert calc.grid("window")[9, 16] == pytest.approx(1.5)
    assert calc.peak("window") == pytest.approx(1.5)


def test_calculator_rejects_bad_settings():
    for kwargs in (dict(cols=2), dict(rows=500), dict(window_minutes=7)):
        with pytest.raises(ValueError):
            HeatmapCalculator(**kwargs)
    with pytest.raises(ValueError):
        HeatmapCalculator().grid("bogus")


def test_calculator_defaults():
    calc = HeatmapCalculator()
    assert (calc.cols, calc.rows, calc.window_minutes) == (32, 18, 5)