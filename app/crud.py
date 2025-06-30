from fastapi import logger
from sqlalchemy import func
from sqlalchemy.orm import Session
from .models import TrendingVideo, VideoDailyMetric
from .schemas import TrendingVideoCreate
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from .models import VideoCategory, VideoCategoryCache

def get_trending_videos(db: Session, country_code: str, skip: int = 0, limit: int = 100) -> List[TrendingVideo]:
    """Retrieves the latest trending videos for a specific country."""
    return db.query(TrendingVideo).filter(TrendingVideo.country_code == country_code).order_by(TrendingVideo.fetched_at.desc()).offset(skip).limit(limit).all()

def get_video_by_id_and_country(db: Session, video_id: str, country_code: str) -> TrendingVideo | None:
    """Retrieves a specific video by its ID and country."""
    return db.query(TrendingVideo).filter(TrendingVideo.video_id == video_id, TrendingVideo.country_code == country_code).order_by(TrendingVideo.fetched_at.desc()).first()

def create_trending_video(db: Session, video: TrendingVideoCreate) -> TrendingVideo:
    db_video = TrendingVideo(**video.model_dump())
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video

def update_trending_video(db: Session, db_video: TrendingVideo, update_data: Dict[str, Any]) -> TrendingVideo:
    for key, value in update_data.items():
        setattr(db_video, key, value)
    db.commit()
    db.refresh(db_video)
    return db_video

def add_or_update_trending_video_batch(db: Session, videos_data: List[Dict[str, Any]], country_code: str, categories: Dict[str, str]):
    """
    Adds new trending videos or updates existing ones, including anomaly detection.
    """
    processed_video_ids = set()
    
    try:
        for video_item in videos_data:
            snippet = video_item.get("snippet", {})
            statistics = video_item.get("statistics", {})

            video_id = video_item["id"]
            title = snippet.get("title")
            description = snippet.get("description")
            published_at = datetime.fromisoformat(snippet["publishedAt"].replace('Z', '+00:00'))
            channel_id = snippet.get("channelId")
            channel_title = snippet.get("channelTitle")
            category_id = snippet.get("categoryId")
            category_name = categories.get(category_id, "Unknown")
            view_count = int(statistics.get("viewCount", 0))
            like_count = int(statistics.get("likeCount", 0))
            comment_count = int(statistics.get("commentCount", 0))
            tags = snippet.get("tags")
            thumbnail_url = snippet.get("thumbnails", {}).get("high", {}).get("url")

            existing_video = db.query(TrendingVideo).filter(
                TrendingVideo.video_id == video_id,
                TrendingVideo.country_code == country_code
            ).order_by(TrendingVideo.fetched_at.desc()).first()

            # Set current timestamp for fetched_at
            current_time = datetime.utcnow()
            
            new_video_data = {
                "video_id": video_id,
                "title": title,
                "description": description,
                "published_at": published_at,
                "channel_id": channel_id,
                "channel_title": channel_title,
                "category_id": category_id,
                "category_name": category_name,
                "view_count": view_count,
                "like_count": like_count,
                "comment_count": comment_count,
                "tags": tags,
                "thumbnail_url": thumbnail_url,
                "country_code": country_code,
                "fetched_at": current_time
            }

            if existing_video:
                # Update existing video's latest data
                new_video_data["previous_view_count"] = existing_video.view_count
                view_count_change = view_count - existing_video.view_count
                new_video_data["view_count_change"] = view_count_change

                # Anomaly Detection (Simple example: 50% view increase)
                viral_spike_threshold = 0.5  # 50% increase
                if existing_video.view_count > 0 and (view_count_change / existing_video.view_count) >= viral_spike_threshold:
                    new_video_data["is_viral_spike"] = True
                    new_video_data["alert_triggered"] = False # Reset to allow new alerts if it keeps spiking
                else:
                    new_video_data["is_viral_spike"] = False

                # Update the existing video
                for key, value in new_video_data.items():
                    setattr(existing_video, key, value)
            else:
                # Create a new entry
                db_video = TrendingVideo(**new_video_data)
                db.add(db_video)
            
            processed_video_ids.add(video_id)
        
        # Commit all changes in one transaction
        db.commit()
        
    except Exception as e:
        # Rollback in case of any error
        db.rollback()
        raise e


def get_daily_metrics_for_video(db: Session, video_id: str, country_code: str, days: int = 7) -> List[VideoDailyMetric]:
    """Retrieves daily metrics for a specific video."""
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    return db.query(VideoDailyMetric).filter(
        VideoDailyMetric.video_id == video_id,
        VideoDailyMetric.country_code == country_code,
        VideoDailyMetric.date >= start_date,
        VideoDailyMetric.date <= end_date
    ).order_by(VideoDailyMetric.date).all()

def get_alerts(db: Session, country_code: Optional[str] = None, triggered_since: Optional[datetime] = None) -> List[TrendingVideo]:
    """Fetches videos that have triggered a viral spike alert."""
    try:
        query = db.query(TrendingVideo).filter(
            TrendingVideo.is_viral_spike == True, 
            TrendingVideo.alert_triggered == False
        )
        
        if country_code:
            query = query.filter(TrendingVideo.country_code == country_code)
        if triggered_since:
            query = query.filter(TrendingVideo.fetched_at >= triggered_since)
        
        # Fetch alerts first
        alerts = query.all()
        
        # Mark alerts as triggered after fetching to avoid re-alerting on the same spike
        for alert in alerts:
            alert.alert_triggered = True
        
        db.commit()
        return alerts
        
    except Exception as e:
        db.rollback()
        raise e

def get_all_country_codes(db: Session) -> List[str]:
    """Returns a list of all unique country codes present in the database."""
    # Fix: Extract the actual values from the result tuples
    result = db.query(TrendingVideo.country_code).distinct().all()
    return [row[0] for row in result if row[0] is not None]

def bulk_create_or_update_videos(db: Session, videos_data: List[Dict[str, Any]], country_code: str, categories: Dict[str, str], batch_size: int = 100):
    """
    More efficient bulk operation for large datasets using SQLAlchemy bulk operations.
    """
    try:
        current_time = datetime.utcnow()
        videos_to_insert = []
        videos_to_update = []
        
        # Process in batches to avoid memory issues
        for i in range(0, len(videos_data), batch_size):
            batch = videos_data[i:i + batch_size]
            video_ids = [video["id"] for video in batch]
            
            # Get existing videos for this batch
            existing_videos = {
                video.video_id: video for video in 
                db.query(TrendingVideo).filter(
                    TrendingVideo.video_id.in_(video_ids),
                    TrendingVideo.country_code == country_code
                ).all()
            }
            
            for video_item in batch:
                snippet = video_item.get("snippet", {})
                statistics = video_item.get("statistics", {})
                video_id = video_item["id"]
                
                video_data = {
                    "video_id": video_id,
                    "title": snippet.get("title"),
                    "description": snippet.get("description"),
                    "published_at": datetime.fromisoformat(snippet["publishedAt"].replace('Z', '+00:00')),
                    "channel_id": snippet.get("channelId"),
                    "channel_title": snippet.get("channelTitle"),
                    "category_id": snippet.get("categoryId"),
                    "category_name": categories.get(snippet.get("categoryId"), "Unknown"),
                    "view_count": int(statistics.get("viewCount", 0)),
                    "like_count": int(statistics.get("likeCount", 0)),
                    "comment_count": int(statistics.get("commentCount", 0)),
                    "tags": snippet.get("tags"),
                    "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                    "country_code": country_code,
                    "fetched_at": current_time
                }
                
                if video_id in existing_videos:
                    existing_video = existing_videos[video_id]
                    video_data["previous_view_count"] = existing_video.view_count
                    view_count_change = video_data["view_count"] - existing_video.view_count
                    video_data["view_count_change"] = view_count_change
                    
                    # Viral spike detection
                    viral_spike_threshold = 0.5
                    if existing_video.view_count > 0 and (view_count_change / existing_video.view_count) >= viral_spike_threshold:
                        video_data["is_viral_spike"] = True
                        video_data["alert_triggered"] = False
                    else:
                        video_data["is_viral_spike"] = False
                    
                    video_data["id"] = existing_video.id  # Include the primary key for update
                    videos_to_update.append(video_data)
                else:
                    videos_to_insert.append(video_data)
        
        # Perform bulk operations
        if videos_to_insert:
            db.bulk_insert_mappings(TrendingVideo, videos_to_insert)
        
        if videos_to_update:
            db.bulk_update_mappings(TrendingVideo, videos_to_update)
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        raise e
    
def save_video_categories_to_db(db: Session, categories: dict):
    """
    Save video categories to database with caching.
    """
    try:
        # Clear existing cache
        db.query(VideoCategoryCache).delete()
        
        # Save new cache
        cache_entry = VideoCategoryCache(
            categories_data=categories,
            last_updated=datetime.utcnow()
        )
        db.add(cache_entry)
        
        # Also save individual categories for easier querying
        db.query(VideoCategory).delete()
        
        for category_id, category_info in categories.items():
            if isinstance(category_info, dict):
                category_name = category_info.get('title', 'Unknown')
                assignable = category_info.get('assignable', 'true')
            else:
                # Handle case where category_info might be just a string
                category_name = str(category_info)
                assignable = 'true'
            
            category = VideoCategory(
                category_id=str(category_id),
                category_name=category_name,
                assignable=assignable,
                last_updated=datetime.utcnow()
            )
            db.add(category)
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        raise

def get_video_categories_from_db(db: Session) -> dict:
    """
    Retrieve video categories from database cache.
    Returns empty dict if no valid cache exists.
    """
    try:
        cache_entry = db.query(VideoCategoryCache).order_by(
            VideoCategoryCache.last_updated.desc()
        ).first()
        
        if cache_entry:
            # Check if cache is still valid (less than 24 hours old)
            cache_age = datetime.utcnow() - cache_entry.last_updated
            if cache_age.total_seconds() < 24 * 60 * 60:  # 24 hours
                return cache_entry.categories_data
        
        return {}
        
    except Exception as e:
        return {}

def should_fetch_categories(db: Session, cache_hours: int = 24) -> bool:
    """
    Check if categories should be fetched from API based on cache age.
    """
    try:
        cache_entry = db.query(VideoCategoryCache).order_by(
            VideoCategoryCache.last_updated.desc()
        ).first()
        
        if not cache_entry:
            return True  # No cache exists, should fetch
        
        cache_age = datetime.utcnow() - cache_entry.last_updated
        return cache_age.total_seconds() > (cache_hours * 60 * 60)
        
    except Exception as e:
        return True  # On error, assume we should fetch

def get_category_name_by_id(db: Session, category_id: str) -> str:
    """
    Get category name by category ID from database.
    """
    try:
        category = db.query(VideoCategory).filter(
            VideoCategory.category_id == str(category_id)
        ).first()
        
        return category.category_name if category else "Unknown Category"
        
    except Exception as e:
        return "Unknown Category"

def get_all_categories(db: Session) -> List[VideoCategory]:
    """
    Get all video categories from database.
    """
    try:
        return db.query(VideoCategory).order_by(VideoCategory.category_name).all()
    except Exception as e:
        return []

def get_categories_stats(db: Session) -> dict:
    """
    Get statistics about cached categories.
    """
    try:
        cache_entry = db.query(VideoCategoryCache).order_by(
            VideoCategoryCache.last_updated.desc()
        ).first()
        
        category_count = db.query(VideoCategory).count()
        
        return {
            "total_categories": category_count,
            "cache_last_updated": cache_entry.last_updated if cache_entry else None,
            "cache_age_hours": (
                (datetime.utcnow() - cache_entry.last_updated).total_seconds() / 3600
                if cache_entry else None
            ),
            "cache_valid": not should_fetch_categories(db) if cache_entry else False
        }
        
    except Exception as e:
        return {
            "total_categories": 0,
            "cache_last_updated": None,
            "cache_age_hours": None,
            "cache_valid": False
        }