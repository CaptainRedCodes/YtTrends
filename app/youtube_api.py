import os
from googleapiclient.discovery import build
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def get_youtube_service():
    """Builds and returns a YouTube Data API service object."""
    if not YOUTUBE_API_KEY:
        logger.error("YOUTUBE_API_KEY not found in environment variables.")
        raise ValueError("YouTube API Key is not set.")
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

def fetch_trending_videos(country_code: str, max_results: int = 50):
    """
    Fetches trending videos for a given country code.
    See: https://developers.google.com/youtube/v3/docs/videos/list
    """
    youtube = get_youtube_service()
    try:
        request = youtube.videos().list(
            part="snippet,statistics",
            chart="mostPopular",
            regionCode=country_code,
            maxResults=max_results,
        )
        response = request.execute()
        return response.get("items", [])
    except Exception as e:
        logger.error(f"Error fetching trending videos for {country_code}: {e}")
        return []

def get_video_categories(country_code: str):
    """Fetches video categories for a given country code."""
    youtube = get_youtube_service()
    try:
        request = youtube.videoCategories().list(
            part="snippet",
            regionCode=country_code
        )
        response = request.execute()
        categories = {item['id']: item['snippet']['title'] for item in response.get('items', [])}
        return categories
    except Exception as e:
        logger.error(f"Error fetching video categories for {country_code}: {e}")
        return {}