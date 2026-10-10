from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DetectionStartRequest(BaseModel):
    camera_id: int = Field(..., gt=0)
    conf: Optional[float] = Field(None, ge=0.05, le=0.95)  # None = use the camera's min_confidence
    imgsz: int = Field(640, ge=320, le=1920)
    track_buffer: int = Field(30, ge=1, le=300)
    realtime: bool = False  # True = drop frames when processing falls behind
    smoothing_seconds: float = Field(5.0, ge=1, le=60)
    initial_count: int = Field(0, ge=0, le=100000)      # people already inside at start
    flow_window_sec: int = Field(60, ge=10, le=600)     # rolling window for F(t)
    growth_window_sec: int = Field(60, ge=10, le=600)   # dt for R(t), minimum 10 s
    occupancy_min_difference: float = Field(3.0, ge=0, le=1000)
    heatmap_save_interval_sec: int = Field(60, ge=0, le=3600)   # 0 = do not save; 5+ recommended
    heatmap_save_mode: str = Field("window", pattern="^(window|instant)$")


class DetectionStopRequest(BaseModel):
    camera_id: int = Field(..., gt=0)

class FlowOut(BaseModel):
    tripwire_configured: bool
    video_time: Optional[float] = None
    in_total: Optional[int] = None
    out_total: Optional[int] = None
    rolling_in: Optional[int] = None
    rolling_out: Optional[int] = None
    net_flow: Optional[int] = None                 # F(t) = rolling_in - rolling_out
    flow_window_sec: Optional[float] = None
    initial_count: Optional[int] = None
    cumulative_occupancy: Optional[int] = None
    growth_rate: Optional[float] = None            # R(t), people per minute
    growth_window_sec: Optional[float] = None      # window actually used
    message: Optional[str] = None                  # e.g. "Tripwire not configured"
    growth_message: Optional[str] = None           # e.g. "not available yet"

class DetectionStatusResponse(BaseModel):
    camera_id: int
    state: str
    source: str
    started_at: datetime
    frames_read: int
    frames_processed: int
    frames_skipped: int
    fps: float                      # measured processing FPS
    target_fps: int
    conf: float                     # confidence threshold in use
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None
    unique_track_ids: int
    tracks_in_memory: int
    run_id: Optional[int] = None
    snapshots_saved: int = 0
    db_errors: int = 0
    error: Optional[str] = None
    flow: Optional[FlowOut] = None
    heatmaps_saved: int = 0
    heatmap_errors: int = 0


class BBox(BaseModel):
    x: int
    y: int
    width: int
    height: int

class Point(BaseModel):
    x: int
    y: int


class TrackOut(BaseModel):
    track_id: int
    confidence: float
    bbox: BBox
    foot_point: Point
    counted: bool = True


class MetricsOut(BaseModel):
    mode: Optional[str] = None             # "full_frame" or "zone" (live only)
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None
    area_sqm: Optional[float] = None
    people_count: int                      # N(t)
    people_count_smoothed: Optional[float] = None  # live only
    density: Optional[float] = None        # D(t), people per m2
    density_smoothed: Optional[float] = None
    message: Optional[str] = None


class DetectionResultsResponse(BaseModel):
    camera_id: int
    run_id: Optional[int] = None
    source: str                      # "live" or "database"
    frame_number: Optional[int] = None     # only known for live results
    timestamp: datetime
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None
    people_detected: int
    tracks: List[TrackOut]
    metrics: Optional[MetricsOut] = None
    flow: Optional[FlowOut] = None


class CountPoint(BaseModel):
    ts: datetime
    person_count: int
    density: Optional[float] = None


class DetectionHistoryResponse(BaseModel):
    camera_id: int
    count: int
    points: List[CountPoint]