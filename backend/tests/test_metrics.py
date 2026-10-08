import pytest

from app.services.vision.metrics import (
    AREA_NOT_CONFIGURED,
    MetricsCalculator,
    MonitorArea,
    MovingAverage,
    compute_density,
    foot_point,
    point_in_polygon,
)
from app.services.vision.results import TrackedPerson

SQUARE = [[0.25, 0.25], [0.75, 0.25], [0.75, 0.75], [0.25, 0.75]]
TRIANGLE = [[0, 0], [1, 0], [0.5, 1]]
L_SHAPE = [[0, 0], [1, 0], [1, 0.5], [0.5, 0.5], [0.5, 1], [0, 1]]


def make_person(foot_x, foot_y, track_id=1):
    return TrackedPerson(
        track_id=track_id, confidence=0.9,
        x=foot_x - 10, y=foot_y - 50, width=20, height=50,
        foot_x=foot_x, foot_y=foot_y,
    )


# ---------- foot point ----------
@pytest.mark.parametrize("box, expected", [
    ((100, 50, 200, 300), (150, 300)),   # bottom-centre
    ((0, 0, 5, 10), (2, 10)),            # odd width: integer division
    ((40, 10, 40, 90), (40, 90)),        # zero-width box
])
def test_foot_point(box, expected):
    assert foot_point(*box) == expected


def test_foot_point_uses_bottom_edge_not_centre():
    _x, y = foot_point(0, 100, 50, 200)
    assert y == 200


# ---------- point in polygon ----------
@pytest.mark.parametrize("x, y, expected", [
    (0.5, 0.5, True),
    (0.1, 0.5, False),
    (0.9, 0.5, False),
    (0.5, 0.1, False),
    (0.5, 0.9, False),
])
def test_point_in_square(x, y, expected):
    assert point_in_polygon(x, y, SQUARE) is expected


@pytest.mark.parametrize("x, y, expected", [
    (0.5, 0.5, True),
    (0.1, 0.9, False),
])
def test_point_in_triangle(x, y, expected):
    assert point_in_polygon(x, y, TRIANGLE) is expected


@pytest.mark.parametrize("x, y, expected", [
    (0.75, 0.25, True),    # top band
    (0.25, 0.75, True),    # left column
    (0.75, 0.75, False),   # the notch of the L
])
def test_point_in_concave_polygon(x, y, expected):
    assert point_in_polygon(x, y, L_SHAPE) is expected


# ---------- density formula ----------
def test_density_formula():
    assert compute_density(30, 150) == pytest.approx(0.2)
    assert compute_density(0, 100) == 0.0


@pytest.mark.parametrize("area", [None, 0, -5])
def test_density_without_usable_area_is_none(area):
    assert compute_density(10, area) is None


# ---------- moving average ----------
def test_moving_average_drops_old_values():
    avg = MovingAverage(5)
    assert avg.add(10, now=0) == 10
    assert avg.add(20, now=1) == 15
    assert avg.add(30, now=6) == 25      # the value from t=0 has expired
    assert avg.add(5, now=100) == 5      # the newest value is never dropped


# ---------- N(t) and D(t) ----------
def test_area_not_configured():
    calc = MetricsCalculator(MonitorArea(mode="full_frame", area_sqm=None))
    m = calc.update([make_person(100, 100), make_person(200, 100, 2), make_person(300, 100, 3)], 1000, 500)
    assert m.people_count == 3
    assert m.density is None
    assert m.density_smoothed is None
    assert m.message == AREA_NOT_CONFIGURED == "Area not configured"


def test_full_frame_density_uses_camera_area():
    calc = MetricsCalculator(MonitorArea(mode="full_frame", area_sqm=100))
    people = [make_person(50 * i, 100, i) for i in range(1, 6)]
    m = calc.update(people, 1000, 500)
    assert m.mode == "full_frame"
    assert m.people_count == 5
    assert m.density == pytest.approx(0.05)
    assert m.message is None
    assert all(p.counted for p in people)


def test_zone_counts_only_people_inside_and_uses_zone_area():
    zone = MonitorArea(mode="zone", area_sqm=50, polygon=SQUARE, zone_id=7, zone_name="Square")
    calc = MetricsCalculator(zone)
    inside = make_person(500, 250, 1)    # (0.5, 0.5)
    left = make_person(100, 250, 2)      # (0.1, 0.5)
    corner = make_person(900, 450, 3)    # (0.9, 0.9)
    m = calc.update([inside, left, corner], 1000, 500)
    assert m.mode == "zone" and m.zone_id == 7 and m.zone_name == "Square"
    assert m.people_count == 1
    assert m.density == pytest.approx(1 / 50)
    assert [inside.counted, left.counted, corner.counted] == [True, False, False]


def test_zone_mode_without_polygon_falls_back_to_full_frame():
    calc = MetricsCalculator(MonitorArea(mode="zone", area_sqm=100, polygon=None))
    m = calc.update([make_person(10, 10)], 100, 100)
    assert m.mode == "full_frame"
    assert m.people_count == 1


def test_smoothing_averages_count_and_density():
    calc = MetricsCalculator(MonitorArea(area_sqm=100), smoothing_seconds=5)
    calc.update([make_person(10, 10, i) for i in range(10)], 100, 100, now=0)
    m = calc.update([make_person(10, 10, i) for i in range(20)], 100, 100, now=1)
    assert m.people_count == 20
    assert m.people_count_smoothed == pytest.approx(15)
    assert m.density_smoothed == pytest.approx(0.15)


def test_empty_frame_gives_zero_not_error():
    m = MetricsCalculator(MonitorArea(area_sqm=100)).update([], 100, 100)
    assert m.people_count == 0
    assert m.density == 0.0