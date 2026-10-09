import pytest
from pydantic import ValidationError

from app.schemas.tripwire import TripwireUpdate, line_length_in_frame_widths


def make(**overrides):
    data = dict(x1=0.1, y1=0.5, x2=0.9, y2=0.5, in_side="LEFT", cooldown_sec=3)
    data.update(overrides)
    return TripwireUpdate(**data)


def test_valid_horizontal_line():
    tw = make()
    assert tw.in_side.value == "LEFT"
    assert tw.cooldown_sec == 3


def test_valid_vertical_line():
    # long vertical line: 0.8 of the height = 0.45 of the width
    assert make(x1=0.5, x2=0.5, y1=0.1, y2=0.9).in_side.value == "LEFT"


def test_too_short_line_rejected():
    with pytest.raises(ValidationError):
        make(x1=0.45, x2=0.55)  # only 10% of the frame width


def test_short_vertical_line_uses_aspect_ratio():
    # 0.3 of the height is only ~17% of the width -> rejected
    with pytest.raises(ValidationError):
        make(x1=0.5, x2=0.5, y1=0.2, y2=0.5)


def test_exactly_minimum_length_accepted():
    assert make(x1=0.4, x2=0.6).cooldown_sec == 3


def test_zero_length_line_rejected():
    with pytest.raises(ValidationError):
        make(x2=0.1)


@pytest.mark.parametrize("field,value", [("x1", -0.1), ("y2", 1.2), ("x2", 1.0001)])
def test_point_outside_frame_rejected(field, value):
    with pytest.raises(ValidationError):
        make(**{field: value})


def test_bad_in_side_rejected():
    with pytest.raises(ValidationError):
        make(in_side="UP")


def test_negative_cooldown_rejected():
    with pytest.raises(ValidationError):
        make(cooldown_sec=-1)


def test_line_length_pure_function():
    assert line_length_in_frame_widths(0.1, 0.5, 0.9, 0.5) == pytest.approx(0.8)