"""Which values of a FrameResult are saved to metric_snapshots (SRS 8.1.7).

Pure logic: no database, no OpenCV. Only aggregated numbers come out, never
track ids, boxes or foot points.
"""
from typing import Optional


def metric_fields(result) -> Optional[dict]:
    """Column values for one metric_snapshots row, or None if there is nothing to save."""
    metrics = result.metrics
    if metrics is None:
        return None

    fields = {
        "ts": result.timestamp,
        "person_count": metrics.people_count,
        "density": metrics.density,
        "in_count": None,
        "out_count": None,
        "net_flow": None,
        "cumulative_occupancy": None,
        "growth_rate": None,
    }

    flow = getattr(result, "flow", None)
    if flow is not None:
        fields["growth_rate"] = flow.growth_rate      # works without a tripwire
        if flow.tripwire_configured:
            fields["in_count"] = flow.rolling_in
            fields["out_count"] = flow.rolling_out
            fields["net_flow"] = flow.net_flow
            fields["cumulative_occupancy"] = flow.cumulative_occupancy
    return fields