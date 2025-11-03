"""
YouTube URL processing and validation utilities.
"""

import re
from urllib.parse import urlparse, parse_qs
from typing import Optional, List
from dataclasses import dataclass


class URLError(Exception):
    """Base exception for URL processing errors."""
    pass


class InvalidYouTubeURLError(URLError):
    """Raised when a URL is not a valid YouTube URL."""
    pass


class InvalidVideoIDError(URLError):
    """Raised when a video ID format is invalid."""
    pass


@dataclass
class YouTubeURL:
    """Represents a parsed YouTube URL."""
    original_url: str
    video_id: str
    is_playlist: bool = False
    playlist_id: Optional[str] = None
    
    @property
    def normalized_url(self) -> str:
        """Return normalized YouTube watch URL."""
        return f"https://www.youtube.com/watch?v={self.video_id}"


class YouTubeURLProcessor:
    """
    Process and validate YouTube URLs.
    
    Supports various YouTube URL formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID
    - https://m.youtube.com/watch?v=VIDEO_ID
    - https://www.youtube.com/live/VIDEO_ID (live streams)
    - https://www.youtube.com/shorts/VIDEO_ID (YouTube Shorts)
    - https://www.youtube.com/embed/VIDEO_ID (embedded videos)
    - https://www.youtube.com/v/VIDEO_ID (old format)
    """
    
    # YouTube video ID: 11 characters, alphanumeric, underscore, hyphen
    VIDEO_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{11}$')
    
    # Valid YouTube domains
    VALID_DOMAINS = {
        'youtube.com',
        'www.youtube.com',
        'm.youtube.com',
        'youtu.be',
    }
    
    def __init__(self):
        """Initialize URL processor."""
        pass
    
    @classmethod
    def is_valid_video_id(cls, video_id: str) -> bool:
        """
        Check if a string is a valid YouTube video ID.
        
        Args:
            video_id: String to validate
            
        Returns:
            True if valid video ID format
        """
        return bool(cls.VIDEO_ID_PATTERN.match(video_id))
    
    @classmethod
    def extract_video_id(cls, url: str) -> str:
        """
        Extract video ID from a YouTube URL.
        
        Args:
            url: YouTube URL
            
        Returns:
            Video ID string
            
        Raises:
            InvalidYouTubeURLError: If URL is not a valid YouTube URL
            InvalidVideoIDError: If video ID format is invalid
        """
        parsed = urlparse(url)
        
        # Check domain
        domain = parsed.netloc.lower()
        if domain not in cls.VALID_DOMAINS:
            raise InvalidYouTubeURLError(
                f"Invalid YouTube domain: {domain}. "
                f"Expected one of: {', '.join(cls.VALID_DOMAINS)}"
            )
        
        video_id = None
        
        # Handle youtu.be format
        if domain == 'youtu.be':
            # Path is /VIDEO_ID
            video_id = parsed.path.lstrip('/')
            # Remove any additional path components
            if '/' in video_id:
                video_id = video_id.split('/')[0]
        
        # Handle youtube.com formats
        else:
            # Check for /watch path
            if parsed.path == '/watch' or parsed.path.startswith('/watch'):
                query_params = parse_qs(parsed.query)
                video_id = query_params.get('v', [None])[0]
            # Handle /embed/VIDEO_ID format
            elif parsed.path.startswith('/embed/'):
                video_id = parsed.path.split('/embed/')[-1]
            # Handle /v/VIDEO_ID format
            elif parsed.path.startswith('/v/'):
                video_id = parsed.path.split('/v/')[-1]
            # Handle /live/VIDEO_ID format (live streams)
            elif parsed.path.startswith('/live/'):
                video_id = parsed.path.split('/live/')[-1]
            # Handle /shorts/VIDEO_ID format (YouTube Shorts)
            elif parsed.path.startswith('/shorts/'):
                video_id = parsed.path.split('/shorts/')[-1]
        
        if not video_id:
            raise InvalidYouTubeURLError(
                f"Could not extract video ID from URL: {url}"
            )
        
        # Clean video ID (remove query parameters if present)
        if '&' in video_id:
            video_id = video_id.split('&')[0]
        if '?' in video_id:
            video_id = video_id.split('?')[0]
        
        # Validate video ID format
        if not cls.is_valid_video_id(video_id):
            raise InvalidVideoIDError(
                f"Invalid video ID format: {video_id}. "
                f"Expected 11 alphanumeric characters, underscore, or hyphen."
            )
        
        return video_id
    
    @classmethod
    def parse_url(cls, url: str) -> YouTubeURL:
        """
        Parse a YouTube URL and extract video and playlist information.
        
        Args:
            url: YouTube URL to parse
            
        Returns:
            YouTubeURL object with parsed information
            
        Raises:
            InvalidYouTubeURLError: If URL is not valid
        """
        video_id = cls.extract_video_id(url)
        
        # Check for playlist
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        playlist_id = query_params.get('list', [None])[0]
        
        return YouTubeURL(
            original_url=url,
            video_id=video_id,
            is_playlist=bool(playlist_id),
            playlist_id=playlist_id
        )
    
    @classmethod
    def validate_url(cls, url: str) -> bool:
        """
        Validate a YouTube URL without raising exceptions.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid, False otherwise
        """
        try:
            cls.extract_video_id(url)
            return True
        except (InvalidYouTubeURLError, InvalidVideoIDError):
            return False
    
    @classmethod
    def process_urls(cls, urls: List[str]) -> List[YouTubeURL]:
        """
        Process multiple URLs and return valid parsed URLs.
        
        Invalid URLs are skipped with a warning.
        
        Args:
            urls: List of URLs to process
            
        Returns:
            List of parsed YouTubeURL objects
        """
        from utils.logger import get_logger
        logger = get_logger("url_processor")
        
        results = []
        for url in urls:
            try:
                parsed = cls.parse_url(url)
                results.append(parsed)
            except (InvalidYouTubeURLError, InvalidVideoIDError) as e:
                logger.warning(f"Skipping invalid URL '{url}': {e}")
                continue
        
        return results


# Convenience functions
def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL. See YouTubeURLProcessor.extract_video_id."""
    return YouTubeURLProcessor.extract_video_id(url)


def parse_url(url: str) -> YouTubeURL:
    """Parse YouTube URL. See YouTubeURLProcessor.parse_url."""
    return YouTubeURLProcessor.parse_url(url)


def validate_url(url: str) -> bool:
    """Validate YouTube URL. See YouTubeURLProcessor.validate_url."""
    return YouTubeURLProcessor.validate_url(url)


def process_urls(urls: List[str]) -> List[YouTubeURL]:
    """Process multiple URLs. See YouTubeURLProcessor.process_urls."""
    return YouTubeURLProcessor.process_urls(urls)
