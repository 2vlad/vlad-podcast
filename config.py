"""
Configuration settings for YouTube to Podcast converter.
"""

from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass, field
from decouple import config, UndefinedValueError
import sys


class ConfigurationError(Exception):
    """Raised when configuration is invalid or incomplete."""
    pass


@dataclass
class Settings:
    """
    Application settings with validation.
    
    All settings can be overridden via environment variables.
    Required settings: SITE_URL, MEDIA_BASE_URL
    """
    
    # Required settings (must be set via environment or .env)
    site_url: str = field(default_factory=lambda: config('SITE_URL', default=''))
    media_base_url: str = field(default_factory=lambda: config('MEDIA_BASE_URL', default=''))
    
    # Audio settings
    audio_format: Literal['m4a', 'mp3'] = field(
        default_factory=lambda: config('AUDIO_FORMAT', default='m4a', cast=str)
    )
    audio_quality: str = field(
        default_factory=lambda: config('AUDIO_QUALITY', default='best', cast=str)
    )
    
    # Feed settings
    feed_max_items: int = field(
        default_factory=lambda: config('FEED_MAX_ITEMS', default=50, cast=int)
    )
    
    # Podcast metadata
    podcast_title: str = field(
        default_factory=lambda: config('PODCAST_TITLE', default='YouTube to Podcast', cast=str)
    )
    podcast_description: str = field(
        default_factory=lambda: config('PODCAST_DESCRIPTION', 
                                      default='Personal podcast feed generated from YouTube videos', 
                                      cast=str)
    )
    podcast_author: str = field(
        default_factory=lambda: config('PODCAST_AUTHOR', default='Your Name', cast=str)
    )
    podcast_language: str = field(
        default_factory=lambda: config('PODCAST_LANGUAGE', default='en', cast=str)
    )
    podcast_category: str = field(
        default_factory=lambda: config('PODCAST_CATEGORY', default='Technology', cast=str)
    )
    
    # Auto-publish settings
    auto_publish: str = field(
        default_factory=lambda: config('AUTO_PUBLISH', default='manual', cast=str)
    )
    github_repo: Optional[str] = field(
        default_factory=lambda: config('GITHUB_REPO', default=None)
    )
    github_branch: str = field(
        default_factory=lambda: config('GITHUB_BRANCH', default='main', cast=str)
    )
    mave_webdav_url: Optional[str] = field(
        default_factory=lambda: config('MAVE_WEBDAV_URL', default=None)
    )
    mave_username: Optional[str] = field(
        default_factory=lambda: config('MAVE_USERNAME', default=None)
    )
    mave_password: Optional[str] = field(
        default_factory=lambda: config('MAVE_PASSWORD', default=None)
    )
    mave_ftp_host: Optional[str] = field(
        default_factory=lambda: config('MAVE_FTP_HOST', default=None)
    )
    mave_ftp_port: int = field(
        default_factory=lambda: config('MAVE_FTP_PORT', default=21, cast=int)
    )
    
    # Directories (computed from BASE_DIR)
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent)
    
    @property
    def podcast_dir(self) -> Path:
        """Podcast output directory."""
        return self.base_dir / "podcast"
    
    @property
    def media_dir(self) -> Path:
        """Media files directory."""
        return self.podcast_dir / "media"
    
    @property
    def rss_file(self) -> Path:
        """RSS feed file path."""
        return self.podcast_dir / "rss.xml"
    
    def __post_init__(self):
        """Validate settings after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """
        Validate configuration settings.
        
        Raises:
            ConfigurationError: If required settings are missing or invalid.
        """
        errors = []
        
        # Validate required URLs
        if not self.site_url or self.site_url == '':
            errors.append(
                "SITE_URL is required. Set it in .env file or environment variable.\n"
                "Example: SITE_URL=https://username.github.io/my-podcast"
            )
        
        if not self.media_base_url or self.media_base_url == '':
            errors.append(
                "MEDIA_BASE_URL is required. Set it in .env file or environment variable.\n"
                "Example: MEDIA_BASE_URL=https://username.github.io/my-podcast/media"
            )
        
        # Validate URL format
        if self.site_url and not (self.site_url.startswith('http://') or self.site_url.startswith('https://')):
            errors.append(f"SITE_URL must start with http:// or https://, got: {self.site_url}")
        
        if self.media_base_url and not (self.media_base_url.startswith('http://') or self.media_base_url.startswith('https://')):
            errors.append(f"MEDIA_BASE_URL must start with http:// or https://, got: {self.media_base_url}")
        
        # Validate audio format
        if self.audio_format not in ('m4a', 'mp3'):
            errors.append(f"AUDIO_FORMAT must be 'm4a' or 'mp3', got: {self.audio_format}")
        
        # Validate feed max items
        if self.feed_max_items < 1:
            errors.append(f"FEED_MAX_ITEMS must be at least 1, got: {self.feed_max_items}")
        
        if errors:
            error_message = "\n\n".join(["Configuration errors:"] + errors)
            raise ConfigurationError(error_message)
    
    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.podcast_dir.mkdir(exist_ok=True)
        self.media_dir.mkdir(exist_ok=True)
        # Create temp directory for file uploads
        temp_dir = self.podcast_dir / 'temp'
        temp_dir.mkdir(exist_ok=True)
    
    @property
    def yt_dlp_options(self) -> dict:
        """Return yt-dlp options based on configuration."""
        return {
            'format': 'bestaudio/best',
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'outtmpl': str(self.media_dir / '%(id)s.%(ext)s'),
        }


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get or create the global settings instance.
    
    Returns:
        Settings: The global settings instance.
    
    Raises:
        ConfigurationError: If configuration is invalid.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Legacy compatibility - expose settings as module-level variables
def _init_module_vars():
    """Initialize module-level variables for backwards compatibility."""
    try:
        settings = get_settings()
        
        # Expose as module-level variables
        globals()['SITE_URL'] = settings.site_url
        globals()['MEDIA_BASE_URL'] = settings.media_base_url
        globals()['AUDIO_FORMAT'] = settings.audio_format
        globals()['AUDIO_QUALITY'] = settings.audio_quality
        globals()['FEED_MAX_ITEMS'] = settings.feed_max_items
        globals()['BASE_DIR'] = settings.base_dir
        globals()['PODCAST_DIR'] = settings.podcast_dir
        globals()['MEDIA_DIR'] = settings.media_dir
        globals()['RSS_FILE'] = settings.rss_file
        globals()['PODCAST_TITLE'] = settings.podcast_title
        globals()['PODCAST_DESCRIPTION'] = settings.podcast_description
        globals()['PODCAST_AUTHOR'] = settings.podcast_author
        globals()['PODCAST_LANGUAGE'] = settings.podcast_language
        globals()['PODCAST_CATEGORY'] = settings.podcast_category
        globals()['YT_DLP_OPTIONS'] = settings.yt_dlp_options
    except ConfigurationError:
        # Don't fail on import, let the application handle it
        pass


_init_module_vars()
