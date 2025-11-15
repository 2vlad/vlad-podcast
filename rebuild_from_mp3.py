#!/usr/bin/env python3
"""
Rebuild RSS feed from existing MP3 files in media directory.
Reads metadata from old RSS feed if available.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings
from utils.rss_manager import RSSManager, EpisodeData, get_mime_type_from_filename
import xml.etree.ElementTree as ET
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def main():
    """Rebuild RSS feed from MP3 files."""
    settings = get_settings()
    
    logger.info("🔨 Rebuilding RSS feed from MP3 files...")
    logger.info(f"   Media dir: {settings.media_dir}")
    logger.info(f"   Audio format: {settings.audio_format}")
    logger.info("")
    
    # Find all MP3 files
    mp3_files = list(settings.media_dir.glob("*.mp3"))
    
    if not mp3_files:
        logger.error("❌ No MP3 files found in media directory!")
        return
    
    logger.info(f"📁 Found {len(mp3_files)} MP3 files")
    for f in mp3_files:
        size_mb = f.stat().st_size / 1024 / 1024
        logger.info(f"   • {f.name} ({size_mb:.1f} MB)")
    logger.info("")
    
    # Read old RSS to get metadata
    old_metadata = {}
    old_rss_path = Path("docs/rss.xml")
    if old_rss_path.exists():
        logger.info("📖 Reading metadata from old RSS feed...")
        try:
            tree = ET.parse(old_rss_path)
            root = tree.getroot()
            channel = root.find('channel')
            if channel:
                for item in channel.findall('item'):
                    guid = item.find('guid')
                    if guid is not None and guid.text:
                        video_id = guid.text
                        title = item.find('title')
                        desc = item.find('description')
                        link = item.find('link')
                        pubDate = item.find('pubDate')
                        
                        duration_elem = item.find('.//{http://www.itunes.com/dtds/podcast-1.0.dtd}duration')
                        image_elem = item.find('.//{http://www.itunes.com/dtds/podcast-1.0.dtd}image')
                        
                        old_metadata[video_id] = {
                            'title': title.text if title is not None else video_id,
                            'description': desc.text if desc is not None else '',
                            'link': link.text if link is not None else '',
                            'pub_date': pubDate.text if pubDate is not None else None,
                            'duration': duration_elem.text if duration_elem is not None else '00:00',
                            'thumbnail': image_elem.get('href') if image_elem is not None else None,
                        }
                logger.info(f"   Found metadata for {len(old_metadata)} episodes")
        except Exception as e:
            logger.warning(f"   ⚠️  Could not read old RSS: {e}")
    logger.info("")
    
    # Create RSS manager
    rss_manager = RSSManager(
        site_url=settings.site_url,
        media_base_url=settings.media_base_url,
        title=settings.podcast_title,
        description=settings.podcast_description,
        author=settings.podcast_author,
        language=settings.podcast_language,
        category=settings.podcast_category,
        image_url=settings.podcast_image,
    )
    
    # Create new feed
    logger.info("✍️  Creating new RSS feed...")
    fg = rss_manager.create_feed()
    
    # Add episodes
    for mp3_file in mp3_files:
        video_id = mp3_file.stem  # Filename without extension
        file_size = mp3_file.stat().st_size
        audio_url = f"{settings.media_base_url}/{mp3_file.name}"
        mime_type = get_mime_type_from_filename(mp3_file.name)
        
        # Get metadata from old RSS or use defaults
        metadata = old_metadata.get(video_id, {})
        title = metadata.get('title', video_id)
        description = metadata.get('description', title)
        link = metadata.get('link', f'https://youtube.com/watch?v={video_id}')
        duration = metadata.get('duration', '00:00')
        thumbnail = metadata.get('thumbnail')
        
        # Parse pub_date
        pub_date = datetime.now(timezone.utc)
        if metadata.get('pub_date'):
            try:
                from email.utils import parsedate_to_datetime
                pub_date = parsedate_to_datetime(metadata['pub_date'])
            except:
                pass
        
        logger.info(f"   + {title[:60]}...")
        logger.info(f"     File: {mp3_file.name}")
        logger.info(f"     MIME: {mime_type}")
        logger.info(f"     Size: {file_size / 1024 / 1024:.1f} MB")
        
        episode = EpisodeData(
            guid=video_id,
            title=title,
            link=link,
            description=description,
            audio_url=audio_url,
            audio_file_size=file_size,
            audio_mime_type=mime_type,
            pub_date=pub_date,
            duration=duration,
            image_url=thumbnail,
        )
        
        rss_manager.add_episode(fg, episode)
    
    logger.info("")
    logger.info("💾 Saving RSS feed...")
    
    # Save to podcast/rss.xml
    rss_manager.save_feed(fg, settings.rss_file, max_items=settings.feed_max_items)
    logger.info(f"   ✅ Saved to: {settings.rss_file}")
    
    # Also save to docs/rss.xml for GitHub Pages
    docs_rss = Path("docs/rss.xml")
    docs_rss.parent.mkdir(exist_ok=True)
    rss_manager.save_feed(fg, docs_rss, max_items=settings.feed_max_items)
    logger.info(f"   ✅ Saved to: {docs_rss}")
    
    logger.info("")
    logger.info("🎉 RSS feed rebuilt successfully!")
    logger.info(f"📝 Episodes: {len(mp3_files)}")
    logger.info(f"🔗 Feed URL: {settings.site_url}/rss.xml")


if __name__ == '__main__':
    main()
