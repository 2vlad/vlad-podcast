#!/usr/bin/env python3
"""
Regenerate RSS feed with correct URLs after configuration change.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings
from utils.rss_manager import RSSManager, EpisodeData
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Regenerate RSS feed with current settings."""
    try:
        settings = get_settings()
        print(f"🔄 Regenerating RSS feed...")
        print(f"   Site URL: {settings.site_url}")
        print(f"   Media URL: {settings.media_base_url}")
        
        # Create RSS manager with current settings
        rss_manager = RSSManager(
            site_url=settings.site_url,
            media_base_url=settings.media_base_url,
            title=settings.podcast_title,
            description=settings.podcast_description,
            author=settings.podcast_author,
            language=settings.podcast_language,
            category=settings.podcast_category,
        )
        
        # Get existing episodes from current feed
        existing_episodes = []
        if settings.rss_file.exists():
            print(f"📖 Reading existing episodes...")
            # Parse existing feed to get episode data
            import xml.etree.ElementTree as ET
            tree = ET.parse(settings.rss_file)
            root = tree.getroot()
            
            # Find all items in channel
            channel = root.find('channel')
            if channel is not None:
                for item in channel.findall('item'):
                    guid_elem = item.find('guid')
                    if guid_elem is not None and guid_elem.text:
                        video_id = guid_elem.text
                        
                        # Check if media file exists
                        media_file = settings.media_dir / f"{video_id}.{settings.audio_format}"
                        if media_file.exists():
                            # Get episode data
                            title_elem = item.find('title')
                            desc_elem = item.find('description')
                            link_elem = item.find('link')
                            
                            # Get duration
                            duration = '00:00'
                            duration_elem = item.find('.//{http://www.itunes.com/dtds/podcast-1.0.dtd}duration')
                            if duration_elem is not None and duration_elem.text:
                                duration = duration_elem.text
                            
                            # Get publication date
                            pub_date = datetime.now()
                            pub_date_elem = item.find('pubDate')
                            if pub_date_elem is not None and pub_date_elem.text:
                                try:
                                    from email.utils import parsedate_to_datetime
                                    pub_date = parsedate_to_datetime(pub_date_elem.text)
                                except:
                                    pass
                            
                            # Get thumbnail
                            thumbnail_url = None
                            image_elem = item.find('.//{http://www.itunes.com/dtds/podcast-1.0.dtd}image')
                            if image_elem is not None:
                                thumbnail_url = image_elem.get('href')
                            
                            existing_episodes.append({
                                'video_id': video_id,
                                'title': title_elem.text if title_elem is not None else video_id,
                                'description': desc_elem.text if desc_elem is not None else '',
                                'link': link_elem.text if link_elem is not None else f'https://youtube.com/watch?v={video_id}',
                                'duration': duration,
                                'pub_date': pub_date,
                                'thumbnail_url': thumbnail_url,
                                'media_file': media_file,
                            })
            
            print(f"   Found {len(existing_episodes)} existing episodes")
        
        # Recreate feed with correct URLs
        print(f"✍️  Creating new feed...")
        fg = rss_manager.create_feed()
        
        # Add episodes back
        for ep in existing_episodes:
            print(f"   Adding: {ep['title']}")
            
            # Get file info
            file_size = ep['media_file'].stat().st_size
            mime_type = "audio/mp4" if settings.audio_format == "m4a" else "audio/mpeg"
            audio_url = f"{settings.media_base_url}/{ep['media_file'].name}"
            
            # Create episode data
            episode = EpisodeData(
                guid=ep['video_id'],
                title=ep['title'],
                link=ep['link'],
                description=ep['description'],
                audio_url=audio_url,
                audio_file_size=file_size,
                audio_mime_type=mime_type,
                pub_date=ep['pub_date'],
                duration=ep['duration'],
                image_url=ep['thumbnail_url'],
            )
            
            rss_manager.add_episode(fg, episode)
        
        # Save feed
        print(f"💾 Saving feed...")
        rss_manager.save_feed(fg, settings.rss_file, max_items=settings.feed_max_items)
        
        print(f"\n✅ Feed regenerated successfully!")
        print(f"📁 RSS file: {settings.rss_file}")
        print(f"📝 Episodes: {len(existing_episodes)}")
        
        # Show URLs
        print(f"\n🌐 Your podcast URLs:")
        print(f"   RSS Feed: {settings.site_url}/rss.xml")
        print(f"   Media: {settings.media_base_url}/")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
