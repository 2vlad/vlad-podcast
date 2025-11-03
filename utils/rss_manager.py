"""
RSS feed generation and management for podcast episodes.
"""

from pathlib import Path
from datetime import datetime
from typing import List, Optional
from feedgen.feed import FeedGenerator
from feedgen.entry import FeedEntry
import xml.etree.ElementTree as ET
from dataclasses import dataclass
import logging

logger = logging.getLogger("rss_manager")


@dataclass
class EpisodeData:
    """Data for a podcast episode."""
    guid: str  # Unique identifier (usually video_id)
    title: str
    link: str  # URL to original video
    description: str
    audio_url: str  # URL to audio file
    audio_file_size: int  # File size in bytes
    audio_mime_type: str  # e.g., "audio/mp4" or "audio/mpeg"
    pub_date: datetime
    duration: str  # HH:MM:SS format
    image_url: Optional[str] = None


class RSSManager:
    """Manage RSS podcast feed generation and updates."""
    
    def __init__(
        self,
        site_url: str,
        media_base_url: str,
        title: str = "YouTube to Podcast",
        description: str = "Personal podcast feed",
        author: str = "Podcast Creator",
        language: str = "en",
        category: str = "Technology",
        image_url: Optional[str] = None,
    ):
        """
        Initialize RSS manager.
        
        Args:
            site_url: Base URL for the podcast site
            media_base_url: Base URL for media files
            title: Podcast title
            description: Podcast description
            author: Author name
            language: Language code (e.g., 'en')
            category: iTunes category
            image_url: URL to podcast cover image
        """
        self.site_url = site_url.rstrip('/')
        self.media_base_url = media_base_url.rstrip('/')
        self.title = title
        self.description = description
        self.author = author
        self.language = language
        self.category = category
        self.image_url = image_url
    
    def create_feed(self) -> FeedGenerator:
        """
        Create a new RSS feed with iTunes podcast tags.
        
        Returns:
            FeedGenerator instance
        """
        fg = FeedGenerator()
        
        # Basic RSS fields
        fg.title(self.title)
        fg.description(self.description)
        fg.link(href=self.site_url, rel='alternate')
        fg.language(self.language)
        fg.generator('YouTube to Podcast v0.1.0')
        
        # Add atom:self link (required for proper RSS)
        rss_url = f"{self.site_url}/rss.xml"
        fg.link(href=rss_url, rel='self', type='application/rss+xml')
        
        # iTunes podcast tags
        fg.load_extension('podcast')
        fg.podcast.itunes_author(self.author)
        fg.podcast.itunes_category(self.category)
        fg.podcast.itunes_explicit('no')
        fg.podcast.itunes_owner(name=self.author, email='podcast@example.com')
        
        if self.image_url:
            try:
                fg.podcast.itunes_image(self.image_url)
                fg.image(url=self.image_url, title=self.title)
            except Exception as e:
                logger.warning(f"Could not add podcast cover image: {e}")
        
        return fg
    
    def add_episode(self, fg: FeedGenerator, episode: EpisodeData) -> FeedEntry:
        """
        Add an episode to the feed.
        
        Args:
            fg: FeedGenerator instance
            episode: Episode data
            
        Returns:
            FeedEntry instance
        """
        fe = fg.add_entry()
        
        # Basic episode fields
        fe.id(episode.guid)
        fe.guid(episode.guid, permalink=False)
        fe.title(episode.title)
        fe.link(href=episode.link)
        fe.description(episode.description)
        fe.pubDate(episode.pub_date)
        
        # Enclosure (audio file)
        fe.enclosure(
            url=episode.audio_url,
            length=str(episode.audio_file_size),
            type=episode.audio_mime_type
        )
        
        # iTunes episode tags
        fe.podcast.itunes_duration(episode.duration)
        if episode.image_url:
            try:
                # Try to add thumbnail, but skip if format is not supported (e.g., WebP)
                fe.podcast.itunes_image(episode.image_url)
            except Exception as e:
                logger.warning(f"Could not add thumbnail for episode {episode.guid}: {e}")
        
        return fe
    
    def load_existing_feed(self, rss_file: Path) -> Optional[FeedGenerator]:
        """
        Load existing RSS feed from file.
        
        Args:
            rss_file: Path to existing RSS file
            
        Returns:
            FeedGenerator instance or None if file doesn't exist
        """
        if not rss_file.exists():
            return None
        
        try:
            fg = FeedGenerator()
            fg.load_extension('podcast')
            
            # Parse existing XML
            tree = ET.parse(rss_file)
            root = tree.getroot()
            
            # Extract channel info
            channel = root.find('channel')
            if channel is not None:
                title = channel.find('title')
                if title is not None and title.text:
                    fg.title(title.text)
                else:
                    fg.title(self.title)
                
                desc = channel.find('description')
                if desc is not None and desc.text:
                    fg.description(desc.text)
                else:
                    fg.description(self.description)
                
                link = channel.find('link')
                if link is not None and link.text:
                    fg.link(href=link.text, rel='alternate')
                else:
                    fg.link(href=self.site_url, rel='alternate')
            
            # Add self link
            rss_url = f"{self.site_url}/rss.xml"
            fg.link(href=rss_url, rel='self', type='application/rss+xml')
            
            # iTunes tags
            fg.podcast.itunes_author(self.author)
            fg.podcast.itunes_category(self.category)
            
            return fg
            
        except Exception as e:
            logger.warning(f"Failed to load existing feed: {e}")
            return None
    
    def get_existing_guids(self, rss_file: Path) -> set:
        """
        Get set of existing episode GUIDs from RSS file.
        
        Args:
            rss_file: Path to RSS file
            
        Returns:
            Set of GUID strings
        """
        if not rss_file.exists():
            return set()
        
        try:
            tree = ET.parse(rss_file)
            root = tree.getroot()
            
            guids = set()
            channel = root.find('channel')
            if channel is not None:
                for item in channel.findall('item'):
                    guid_elem = item.find('guid')
                    if guid_elem is not None and guid_elem.text:
                        guids.add(guid_elem.text)
            
            return guids
            
        except Exception as e:
            logger.warning(f"Failed to read existing GUIDs: {e}")
            return set()
    
    def save_feed(self, fg: FeedGenerator, rss_file: Path, max_items: Optional[int] = None) -> None:
        """
        Save feed to file, optionally limiting number of items.
        
        Args:
            fg: FeedGenerator instance
            rss_file: Path to save RSS file
            max_items: Maximum number of items to keep (None = no limit)
        """
        # Ensure parent directory exists
        rss_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Limit items if requested
        if max_items and max_items > 0:
            entries = fg.entry()
            if len(entries) > max_items:
                # Keep only the most recent items
                # Note: feedgen doesn't have a built-in way to remove entries,
                # so we'd need to regenerate the feed
                logger.warning(f"Feed has {len(entries)} items, but max is {max_items}. Trimming not yet implemented.")
        
        # Write RSS file
        fg.rss_file(str(rss_file), pretty=True)
        logger.info(f"Saved RSS feed to {rss_file}")
