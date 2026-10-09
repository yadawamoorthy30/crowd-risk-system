from decimal import Decimal
from types import SimpleNamespace

from app.models.tripwire import InSide
from app.services.vision.flow import TripwireLine


def make_row(side):
    return SimpleNamespace(
        x1=Decimal("0.00078"), y1=Decimal("0.45278"),
        x2=Decimal("0.99844"), y2=Decimal("0.48333"),
        in_side=side, cooldown_sec=3,
    )


def test_from_model_converts_decimal_and_enum():
    line = TripwireLine.from_model(make_row(InSide.LEFT))
    assert (line.x1, line.y1, line.x2, line.y2) == (0.00078, 0.45278, 0.99844, 0.48333)
    assert line.in_side == "LEFT"
    assert line.in_sign == -1
    assert line.cooldown_sec == 3.0


def test_from_model_accepts_plain_string_side():
    line = TripwireLine.from_model(make_row("RIGHT"))
    assert line.in_side == "RIGHT"
    assert line.in_sign == 1