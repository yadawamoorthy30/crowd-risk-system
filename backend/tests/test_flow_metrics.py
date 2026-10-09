from datetime import datetime
from types import SimpleNamespace

import pytest

from app.services.vision.flow import CrossingEvent
from app.services.vision.flow_metrics import (
    FlowMetricsCalculator, GrowthRateCalculator,
    cumulative_occupancy, net_flow, rolling_in_out,
)


def ev(video_time, direction):
    return CrossingEvent(datetime.now(), video_time, direction)


# ---------- rolling IN/OUT and net flow ----------

def test_rolling_in_out_counts_only_the_window():
    events = [ev(10, "IN"), ev(20, "IN"), ev(50, "OUT"), ev(70, "IN")]
    assert rolling_in_out(events, now=75, window_sec=60) == (2, 1)   # 10 s is too old


def test_rolling_window_boundaries():
    events = [ev(15, "IN"), ev(75, "OUT")]
    # (15, 75]: the event exactly at now-window is out, the one at now is in
    assert rolling_in_out(events, now=75, window_sec=60) == (0, 1)


def test_net_flow_is_in_minus_out():
    assert net_flow(5, 2) == 3
    assert net_flow(1, 4) == -3


# ---------- cumulative occupancy ----------

def test_cumulative_occupancy_adds_initial_count():
    assert cumulative_occupancy(5, 8, 3) == 10


def test_cumulative_occupancy_is_not_clamped():
    assert cumulative_occupancy(0, 1, 4) == -3


# ---------- growth rate ----------

def feed(calc, n_of_t, seconds):
    rate = None
    for t in range(seconds + 1):
        rate = calc.update(n_of_t(t), float(t))
    return rate


def test_growth_steady_is_zero():
    assert feed(GrowthRateCalculator(60), lambda t: 20, 90) == pytest.approx(0.0)


def test_growth_growing():
    # +1 person every 3 s = +20 per minute
    assert feed(GrowthRateCalculator(60), lambda t: 20 + t / 3, 90) == pytest.approx(20.0)


def test_growth_shrinking():
    # -1 person every 6 s = -10 per minute
    assert feed(GrowthRateCalculator(60), lambda t: 100 - t / 6, 90) == pytest.approx(-10.0)


def test_growth_warming_up_then_partial_window():
    calc = GrowthRateCalculator(60)
    assert calc.update(20, 0.0) is None
    assert calc.update(22, 5.0) is None          # under the 10 s minimum
    assert calc.update(25, 10.0) == pytest.approx(30.0)   # +5 in 10 s
    assert calc.last_window_sec == pytest.approx(10.0)


def test_growth_window_shorter_than_dt_uses_available_history():
    calc = GrowthRateCalculator(60)
    calc.update(0, 0.0)
    assert calc.update(10, 30.0) == pytest.approx(20.0)   # only 30 s of history


def test_growth_window_below_minimum_rejected():
    with pytest.raises(ValueError):
        GrowthRateCalculator(5)


def test_growth_history_is_pruned():
    calc = GrowthRateCalculator(60)
    feed(calc, lambda t: 10, 600)
    assert len(calc._items) <= 62


# ---------- combined calculator ----------

def test_calculator_without_tripwire_still_computes_growth():
    calc = FlowMetricsCalculator()
    first = calc.update(None, 12.0, 0.0)
    assert first.growth_rate is None and first.growth_message
    second = calc.update(None, 18.0, 20.0)
    assert second.tripwire_configured is False
    assert second.net_flow is None and second.cumulative_occupancy is None
    assert second.message == "Tripwire not configured"
    assert second.growth_rate == pytest.approx(18.0)      # +6 in 20 s


def test_calculator_with_tripwire():
    counter = SimpleNamespace(
        in_total=3, out_total=1,
        events=[ev(10, "IN"), ev(30, "IN"), ev(40, "OUT"), ev(65, "IN")],
    )
    calc = FlowMetricsCalculator(initial_count=2, flow_window_sec=60, growth_window_sec=60)
    m = calc.update(counter, 10.0, 70.0)
    assert m.tripwire_configured is True
    assert (m.rolling_in, m.rolling_out, m.net_flow) == (2, 1, 1)
    assert (m.in_total, m.out_total) == (3, 1)
    assert m.cumulative_occupancy == 4                    # 2 + 3 - 1