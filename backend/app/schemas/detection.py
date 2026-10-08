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


class DetectionStopRequest(BaseModel):
    camera_id: int = Field(..., gt=0)


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


class CountPoint(BaseModel):
    ts: datetime
    person_count: int
    density: Optional[float] = None


class DetectionHistoryResponse(BaseModel):
    camera_id: int
    count: int
    points: List[CountPoint]