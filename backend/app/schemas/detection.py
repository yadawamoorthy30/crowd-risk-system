from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DetectionStartRequest(BaseModel):
    camera_id: int = Field(..., gt=0)
    conf: Optional[float] = Field(None, ge=0.05, le=0.95)  # None = use the camera's min_confidence
    imgsz: int = Field(640, ge=320, le=1920)
    track_buffer: int = Field(30, ge=1, le=300)
    realtime: bool = False  # True = drop frames when processing falls behind


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


class DetectionResultsResponse(BaseModel):
    camera_id: int
    run_id: Optional[int] = None
    source: str                      # "live" or "database"
    frame_number: int
    timestamp: datetime
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None
    people_detected: int
    tracks: List[TrackOut]


class CountPoint(BaseModel):
    run_id: int
    frame_number: int
    captured_at: datetime
    people_count: int


class DetectionHistoryResponse(BaseModel):
    camera_id: int
    count: int
    points: List[CountPoint]