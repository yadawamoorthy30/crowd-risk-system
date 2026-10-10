from datetime import datetime

from app.services.vision.flow_metrics import FlowMetrics
from app.services.vision.results import FrameMetrics, FrameResult
from app.services.vision.snapshot_fields import metric_fields

NOW = datetime(2026, 10, 10, 12, 0, 0)


def make_metrics(count=7, density=0.35):
    return FrameMetrics(
        mode="full_frame", zone_id=None, zone_name=None, area_sqm=20.0,
        people_count=count, people_count_smoothed=float(count),
        density=density, density_smoothed=density,
    )


def make_result(metrics=None, flow=None):
    return FrameResult(frame_number=1, timestamp=NOW, metrics=metrics, flow=flow)


def test_no_metrics_returns_none():
    assert metric_fields(make_result(metrics=None)) is None


def test_without_flow_keeps_old_columns_and_nulls():
    fields = metric_fields(make_result(make_metrics()))
    assert fields["ts"] == NOW
    assert fields["person_count"] == 7
    assert fields["density"] == 0.35
    for name in ("in_count", "out_count", "net_flow", "cumulative_occupancy", "growth_rate"):
        assert fields[name] is None


def test_with_tripwire_maps_rolling_values():
    flow = FlowMetrics(
        video_time=42.0, tripwire_configured=True,
        in_total=9, out_total=4, rolling_in=3, rolling_out=1, net_flow=2,
        cumulative_occupancy=8, growth_rate=6.5,
    )
    fields = metric_fields(make_result(make_metrics(), flow))
    assert fields["in_count"] == 3          # rolling window, not the 9 total
    assert fields["out_count"] == 1
    assert fields["net_flow"] == 2
    assert fields["cumulative_occupancy"] == 8
    assert fields["growth_rate"] == 6.5


def test_without_tripwire_only_growth_rate_is_saved():
    flow = FlowMetrics(video_time=42.0, tripwire_configured=False, growth_rate=-2.5)
    fields = metric_fields(make_result(make_metrics(), flow))
    assert fields["growth_rate"] == -2.5
    assert fields["in_count"] is None
    assert fields["cumulative_occupancy"] is None


def test_growth_warming_up_is_saved_as_null():
    flow = FlowMetrics(video_time=3.0, tripwire_configured=True,
                       rolling_in=0, rolling_out=0, net_flow=0,
                       cumulative_occupancy=0, growth_rate=None)
    assert metric_fields(make_result(make_metrics(), flow))["growth_rate"] is None


def test_only_aggregated_columns_can_be_written():
    # privacy rule (SRS 8.1.7): no track ids, boxes or positions
    fields = metric_fields(make_result(make_metrics()))
    assert set(fields) == {
        "ts", "person_count", "density", "in_count", "out_count",
        "net_flow", "cumulative_occupancy", "growth_rate",
    }