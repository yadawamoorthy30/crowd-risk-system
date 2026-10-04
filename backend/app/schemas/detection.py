from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DetectionStartRequest(BaseModel):
    camera_id: int = Field(..., gt=0)
    conf: float = Field(0.25, ge=0.05, le=0.95)
    imgsz: int = Field(640, ge=320, le=1920)


class DetectionStopRequest(BaseModel):
    camera_id: int = Field(..., gt=0)


class DetectionStatusResponse(BaseModel):
    camera_id: int
    state: str
    source: str
    started_at: datetime
    frames_processed: int
    fps: float
    unique_track_ids: int
    run_id: Optional[int] = None
    snapshots_saved: int = 0
    db_errors: int = 0
    error: Optional[str] = None


class BBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class TrackOut(BaseModel):
    track_id: int
    confidence: float
    bbox: BBox


class DetectionResultsResponse(BaseModel):
    camera_id: int
    run_id: Optional[int] = None
    source: str                      # "live" or "database"
    frame_number: int
    timestamp: datetime
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