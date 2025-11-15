#!/usr/bin/env python3
"""
Fix RSS feed namespace issues and ensure all required iTunes tags are present.
This script regenerates the RSS feed from scratch with proper namespaces.
"""

import sys
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Settings
from utils.rss_manager import RSSManager, EpisodeData, get_mime_type_from_filename

# Initialize settings
settings = Settings()

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def parse_existing_episodes(rss_file: Path) -> list[dict]:
    """
    Parse existing RSS file to extract episode data.
    
    Args:
        rss_file: Path to existing RSS file
        
    Returns:
        List of episode data dictionaries
    """
    episodes = []
    
    if not rss_file.exists():
        logger.warning(f"RSS file not found: {rss_file}")
        return episodes
    
    try:
        tree = ET.parse(rss_file)
        root = tree.getroot()
        
        # Handle both with and without namespace prefix
        channel = root.find('channel')
        if channel is None:
            channel = root.find('{http://www.w3.org/2005/Atom}channel')
        
        if channel is None:
            logger.error("Could not find channel element in RSS")
            return episodes
        
        # Find all items
        items = channel.findall('item')
        logger.info(f"Found {len(items)} episode(s) in existing feed")
        
        for item in items:
            # Extract episode data
            guid = item.findtext('guid', '')
            title = item.findtext('title', '')
            link = item.findtext('link', '')
            description = item.findtext('description', '')
            pub_date_str = item.findtext('pubDate', '')
            
            # Parse enclosure
            enclosure = item.find('enclosure')
            if enclosure is None:
                logger.warning(f"Episode {guid} missing enclosure, skipping")
                continue
            
            audio_url = enclosure.get('url', '')
            audio_size = int(enclosure.get('length', 0))
            audio_type = enclosure.get('type', 'audio/mpeg')
            
            # Parse duration (iTunes tag with namespace)
            duration = None
            for ns in ['', '{http://www.itunes.com/dtds/podcast-1.0.dtd}']:
                duration_elem = item.find(f'{ns}duration')
                if duration_elem is not None:
                    duration = duration_elem.text
                    break
            
            # Parse thumbnail (iTunes image with namespace)
            thumbnail = None
            for ns in ['', '{http://www.itunes.com/dtds/podcast-1.0.dtd}']:
                image_elem = item.find(f'{ns}image')
                if image_elem is not None:
                    thumbnail = image_elem.get('href')
                    break
            
            # Parse pubDate
            pub_date = datetime.now()
            if pub_date_str:
                try:
                    from email.utils import parsedate_to_datetime
                    pub_date = parsedate_to_datetime(pub_date_str)
                except:
                    logger.warning(f"Could not parse pubDate: {pub_date_str}")
            
            episodes.append({
                'guid': guid,
                'title': title,
                'link': link,
                'description': description,
                'audio_url': audio_url,
                'audio_size': audio_size,
                'audio_type': audio_type,
                'pub_date': pub_date,
                'duration': duration or '00:00:00',
                'thumbnail': thumbnail,
            })
            
            logger.info(f"  - {title[:60]}...")
        
    except Exception as e:
        logger.error(f"Error parsing RSS file: {e}")
        import traceback
        traceback.print_exc()
    
    return episodes


def main():
    """Regenerate RSS feed with proper namespaces."""
    
    logger.info("=" * 60)
    logger.info("RSS Namespace Fix Tool")
    logger.info("=" * 60)
    
    # Check if RSS file exists
    if not settings.rss_file.exists():
        logger.error(f"RSS file not found: {settings.rss_file}")
        logger.error("Nothing to fix!")
        return 1
    
    # Backup existing RSS
    backup_file = settings.rss_file.with_suffix('.xml.backup')
    import shutil
    shutil.copy2(settings.rss_file, backup_file)
    logger.info(f"✓ Backed up existing RSS to: {backup_file}")
    
    # Parse existing episodes
    logger.info("\n📖 Parsing existing episodes...")
    episodes_data = parse_existing_episodes(settings.rss_file)
    
    if not episodes_data:
        logger.warning("No episodes found in existing feed")
        return 1
    
    logger.info(f"✓ Found {len(episodes_data)} episode(s)")
    
    # Create RSS manager with proper configuration
    logger.info("\n✍️  Creating new RSS feed with proper namespaces...")
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
    
    # Create fresh feed (not loading existing one to avoid namespace issues)
    fg = rss_manager.create_feed()
    logger.info("✓ Created new feed structure")
    
    # Add all episodes to the new feed
    logger.info("\n📝 Adding episodes to new feed...")
    for ep_data in episodes_data:
        episode = EpisodeData(
            guid=ep_data['guid'],
            title=ep_data['title'],
            link=ep_data['link'],
            description=ep_data['description'],
            audio_url=ep_data['audio_url'],
            audio_file_size=ep_data['audio_size'],
            audio_mime_type=ep_data['audio_type'],
            pub_date=ep_data['pub_date'],
            duration=ep_data['duration'],
            image_url=ep_data['thumbnail'],
        )
        rss_manager.add_episode(fg, episode)
        logger.info(f"  ✓ {ep_data['title'][:60]}...")
    
    # Save the new feed
    logger.info("\n💾 Saving new RSS feed...")
    rss_manager.save_feed(fg, settings.rss_file, max_items=settings.feed_max_items)
    logger.info(f"✓ Saved to: {settings.rss_file}")
    
    # Verify the new feed
    logger.info("\n✅ Verifying new feed...")
    tree = ET.parse(settings.rss_file)
    root = tree.getroot()
    
    # Check namespaces
    logger.info("\nNamespaces in new feed:")
    for prefix, uri in root.attrib.items():
        if prefix.startswith('{'):
            prefix = prefix[1:-1]
        logger.info(f"  - {prefix}: {uri}")
    
    # Check for required tags
    channel = root.find('channel')
    if channel:
        has_language = channel.find('language') is not None
        logger.info(f"\n<language> tag present: {has_language}")
        
        # Check for iTunes tags (with proper namespace)
        itunes_ns = '{http://www.itunes.com/dtds/podcast-1.0.dtd}'
        has_itunes_author = channel.find(f'{itunes_ns}author') is not None
        has_itunes_image = channel.find(f'{itunes_ns}image') is not None
        has_itunes_explicit = channel.find(f'{itunes_ns}explicit') is not None
        has_itunes_owner = channel.find(f'{itunes_ns}owner') is not None
        
        logger.info(f"<itunes:author> tag present: {has_itunes_author}")
        logger.info(f"<itunes:image> tag present: {has_itunes_image}")
        logger.info(f"<itunes:explicit> tag present: {has_itunes_explicit}")
        logger.info(f"<itunes:owner> tag present: {has_itunes_owner}")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ RSS feed regenerated successfully!")
    logger.info(f"📁 Feed location: {settings.rss_file}")
    logger.info(f"📁 Backup location: {backup_file}")
    logger.info(f"🔗 Feed URL: {settings.site_url}/rss.xml")
    logger.info("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
