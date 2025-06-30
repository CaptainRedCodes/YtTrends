from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any

class VideoBase(BaseModel):
    video_id: str
    title: str
    description: Optional[str] = None
    published_at: datetime
    channel_id: str
    channel_title: str
    category_id: str
    category_name: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    tags: Optional[List[str]] = None
    thumbnail_url: Optional[str] = None
    country_code: str

class TrendingVideoCreate(VideoBase):
    pass

class TrendingVideoResponse(VideoBase):
    id: int
    fetched_at: datetime
    previous_view_count: Optional[int] = None
    view_count_change: Optional[int] = None
    is_viral_spike: bool
    alert_triggered: bool

    class Config:
        from_attributes = True # Or orm_mode = True for older Pydantic

class Alert(BaseModel):
    video_id: str
    title: str
    country_code: str
    alert_type: str
    current_views: int
    previous_views: int
    view_change: int
    timestamp: datetime

    class Config:
        from_attributes = True