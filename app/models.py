from datetime import datetime
from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, BigInteger, Float, JSON, UniqueConstraint
from sqlalchemy.sql import func
from .database import Base
from sqlalchemy.orm import declarative_base, Mapped, mapped_column

class TrendingVideo(Base):
    __tablename__ = "trending_videos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    video_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    published_at = Column(DateTime, nullable=False)
    channel_id = Column(String, nullable=False)
    channel_title = Column(String, nullable=False)
    category_id = Column(String, nullable=False)
    category_name = Column(String)
    view_count = Column(BigInteger)
    like_count = Column(BigInteger)
    comment_count = Column(BigInteger)
    tags = Column(JSON) # Store as JSON array
    thumbnail_url = Column(String)
    country_code = Column(String, index=True, nullable=False)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())

    # Fields for anomaly detection / historical tracking
    previous_view_count = Column(BigInteger)
    view_count_change = Column(BigInteger)
    is_viral_spike = Column(Boolean, default=False) # Flag for sudden spikes
    alert_triggered = Column(Boolean, default=False) # To prevent repeated alerts for the same event

    __table_args__ = (
        UniqueConstraint('video_id', 'country_code', name='uq_trending_videos_video_id_country_code'),
    )

class VideoDailyMetric(Base):
    """
    Optional: To store daily snapshots of metrics for more robust anomaly detection
    and historical charting. This would be a more granular approach.
    """
    __tablename__ = "video_daily_metrics"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String, nullable=False)
    country_code = Column(String, nullable=False)
    date = Column(DateTime, nullable=False) # Date of the snapshot
    view_count = Column(BigInteger)
    like_count = Column(BigInteger)
    comment_count = Column(BigInteger)

    # Add a unique constraint to prevent duplicate entries for a video on a given day/country
    __table_args__ = (UniqueConstraint('video_id', 'country_code', 'date', name='_video_country_date_uc'),)

class VideoCategory(Base):
    __tablename__ = "video_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(String(10), unique=True, index=True, nullable=False)
    category_name = Column(String(100), nullable=False)
    assignable = Column(String(10), default="true")
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<VideoCategory(id={self.category_id}, name='{self.category_name}')>"

class VideoCategoryCache(Base):
    __tablename__ = "video_category_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    categories_data = Column(JSON, nullable=False)  # Store the full categories dict
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<VideoCategoryCache(last_updated={self.last_updated})>"