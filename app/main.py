from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from .database import SessionLocal, engine, Base, get_db
from .models import TrendingVideo, VideoDailyMetric, VideoCategory
from .schemas import TrendingVideoResponse, Alert
from .crud import (
    add_or_update_trending_video_batch,
    get_trending_videos,
    get_alerts,
    get_all_country_codes,
    get_video_categories_from_db,
    save_video_categories_to_db,
    should_fetch_categories,
    get_all_categories,
    get_categories_stats
)
from .youtube_api import fetch_trending_videos, get_video_categories
from fastapi_utilities import repeat_every
from datetime import datetime, timedelta
import logging
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

origins = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:3000",  
    "http://localhost:5173",  
    "http://127.0.0.1:3000",  
    "http://127.0.0.1:5173",  
]

Base.metadata.create_all(bind=engine)

TRACKED_COUNTRIES = ["US", "IN", "GB", "CA", "DE", "FR", "JP", "AU"]
FETCH_INTERVAL_SECONDS = 6 * 60 * 60
CATEGORY_CACHE_HOURS = 24

# Store categories for quick lookup
VIDEO_CATEGORIES: dict = {}

async def load_video_categories():
    """
    Load video categories from database or fetch from API if needed.
    """
    global VIDEO_CATEGORIES
    db: Session = SessionLocal()
    
    try:
        # First, try to load from database
        cached_categories = get_video_categories_from_db(db)
        
        if cached_categories:
            VIDEO_CATEGORIES = cached_categories
            logger.info(f"Loaded {len(VIDEO_CATEGORIES)} video categories from database cache.")
            return
        
        # If no cached data or cache is expired, fetch from API
        logger.info("Fetching video categories from YouTube API...")
        fresh_categories = {}
        
        for country in TRACKED_COUNTRIES:
            try:
                categories = await get_video_categories(country)
                if categories:
                    fresh_categories.update(categories)
            except Exception as e:
                logger.error(f"Error fetching categories for {country}: {e}")
        
        if fresh_categories:
            VIDEO_CATEGORIES = fresh_categories
            # Save to database
            save_video_categories_to_db(db, fresh_categories)
            logger.info(f"Fetched and cached {len(VIDEO_CATEGORIES)} video categories.")
        else:
            logger.warning("No video categories could be fetched from API.")
            
    except Exception as e:
        logger.error(f"Error loading video categories: {e}")
    finally:
        db.close()

async def check_and_refresh_categories():
    """
    Check if categories need to be refreshed and update if necessary.
    """
    db: Session = SessionLocal()
    try:
        if should_fetch_categories(db, CATEGORY_CACHE_HOURS):
            logger.info("Categories cache expired, refreshing...")
            await load_video_categories()
        else:
            logger.info("Categories cache is still valid.")
    except Exception as e:
        logger.error(f"Error checking category cache: {e}")
    finally:
        db.close()

async def fetch_and_store_trending_videos_task():
    """
    Background task to periodically fetch trending videos and store them.
    """
    logger.info(f"Starting scheduled fetch of trending videos for {TRACKED_COUNTRIES}...")
    
    db: Session = SessionLocal()
    try:
        # Check if we need to refresh categories
        await check_and_refresh_categories()
        
        # Ensure we have categories loaded
        if not VIDEO_CATEGORIES:
            await load_video_categories()

        for country_code in TRACKED_COUNTRIES:
            try:
                trending_items = fetch_trending_videos(country_code=country_code)
                if trending_items:
                    add_or_update_trending_video_batch(db, trending_items, country_code, VIDEO_CATEGORIES)
                    logger.info(f"Successfully fetched and stored {len(trending_items)} trending videos for {country_code}.")
                else:
                    logger.warning(f"No trending videos found for {country_code}.")
            except Exception as e:
                logger.error(f"Error in background task for {country_code}: {e}")
    except Exception as e:
        logger.error(f"Critical error in background task: {e}")
    finally:
        db.close()
    
    logger.info("Finished scheduled fetch of trending videos.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    
    logger.info("Loading video categories...")
    await load_video_categories()
    
    logger.info("Fetching initial trending videos data...")
    asyncio.create_task(fetch_and_store_trending_videos_task())
    
    # Start the recurring task
    asyncio.create_task(recurring_fetch_task())
    
    yield
    
    logger.info("Application shutting down...")

async def recurring_fetch_task():
    """Recurring task that runs every FETCH_INTERVAL_SECONDS"""
    while True:
        await asyncio.sleep(FETCH_INTERVAL_SECONDS)
        await fetch_and_store_trending_videos_task()

app = FastAPI(
    title="YouTube Trend Tracker API",
    description="API for fetching and tracking trending YouTube videos with alerts.",
    version="1.0.0",
    lifespan=lifespan  # Use the new lifespan parameter
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# --- API Endpoints ---

@app.get("/")
async def root():
    return {
        "message": "Welcome to the YouTube Trend Tracker API!",
        "status": "running",
        "tracked_countries": TRACKED_COUNTRIES,
        "endpoints": {
            "docs": "/docs",
            "trending": "/trending-videos/{country_code}",
            "alerts": "/alerts",
            "countries": "/countries"
        }
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify API is responsive.
    This is a basic liveness check, not a full database connectivity check.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/trending-videos/{country_code}", response_model=List[TrendingVideoResponse])
async def get_latest_trending_videos(
    country_code: str,
    db: Session = Depends(get_db),
    limit: int = 50,
    skip: int = 0
):
    """
    Retrieve the latest trending videos for a specified country.
    """
    if country_code not in TRACKED_COUNTRIES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid country code. Supported codes: {', '.join(TRACKED_COUNTRIES)}"
        )

    try:
        videos = get_trending_videos(db, country_code, skip=skip, limit=limit)
        if not videos:
            raise HTTPException(
                status_code=404, 
                detail="No trending videos found for this country yet. Data collection may be in progress."
            )
        return videos
    except Exception as e:
        logger.error(f"Error fetching trending videos for {country_code}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/countries", response_model=List[str])
async def get_supported_countries(db: Session = Depends(get_db)):
    """
    Get a list of all country codes for which data is being collected.
    """
    try:
        country_codes = get_all_country_codes(db)
        return country_codes if country_codes else TRACKED_COUNTRIES
    except Exception as e:
        logger.error(f"Error fetching country codes: {e}")
        return TRACKED_COUNTRIES

@app.get("/alerts", response_model=List[Alert])
async def get_viral_alerts(
    db: Session = Depends(get_db),
    country_code: Optional[str] = None,
    since_hours: int = 24
):
    """
    Retrieve alerts for sudden viral spikes.
    """
    try:
        triggered_since = datetime.utcnow() - timedelta(hours=since_hours)
        trending_videos = get_alerts(db, country_code, triggered_since)
        
        alerts = []
        for video in trending_videos:
            alerts.append(Alert(
                video_id=video.video_id,
                title=video.title,
                country_code=video.country_code,
                alert_type="Viral Spike",
                current_views=video.view_count,
                previous_views=video.previous_view_count or 0,
                view_change=video.view_count_change or 0,
                timestamp=video.fetched_at
            ))
        return alerts
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """
    Get basic statistics about the data collection.
    """
    try:
        stats = {}
        for country in TRACKED_COUNTRIES:
            count = db.query(TrendingVideo).filter(TrendingVideo.country_code == country).count()
            stats[country] = count
        
        # Get category cache info
        category_cache_info = db.query(VideoCategory).first()
        last_category_update = category_cache_info.last_updated if category_cache_info else None
        
        return {
            "total_videos_tracked": sum(stats.values()),
            "videos_by_country": stats,
            "last_updated": datetime.utcnow(),
            "categories_loaded": len(VIDEO_CATEGORIES),
            "categories_last_updated": last_category_update,
            "categories_cache_valid": not should_fetch_categories(db, CATEGORY_CACHE_HOURS)
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/refresh-categories")
async def refresh_categories(db: Session = Depends(get_db)):
    """
    Manually refresh video categories from YouTube API.
    """
    try:
        logger.info("Manual refresh of video categories requested...")
        await load_video_categories()
        
        return {
            "message": "Video categories refreshed successfully",
            "categories_count": len(VIDEO_CATEGORIES),
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error refreshing categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh categories")

@app.get("/categories")
async def get_video_categories(db: Session = Depends(get_db)):
    """
    Get all cached video categories with their details.
    """
    try:
        categories = get_all_categories(db)
        stats = get_categories_stats(db)
        
        return {
            "categories": [
                {
                    "id": cat.category_id,
                    "name": cat.category_name,
                    "assignable": cat.assignable,
                    "last_updated": cat.last_updated
                }
                for cat in categories
            ],
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch categories")

@app.get("/categories/stats")
async def get_category_stats(db: Session = Depends(get_db)):
    """
    Get statistics about video categories cache.
    """
    try:
        stats = get_categories_stats(db)
        return stats
    except Exception as e:
        logger.error(f"Error fetching category stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch category statistics")