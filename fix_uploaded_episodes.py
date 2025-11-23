#!/usr/bin/env python3
"""
Fix existing uploaded episodes in RSS feed.
- Extract real duration from audio files
- Fix Part X/Y numbering
- Improve descriptions
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings
from utils.rss_manager import RSSManager, EpisodeData
from utils.audio_splitter import AudioSplitter
import xml.etree.ElementTree as ET
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Fix uploaded episodes with correct metadata."""
    try:
        settings = get_settings()
        splitter = AudioSplitter()
        
        print("🔧 Fixing uploaded episodes in RSS feed...")
        print(f"   Media dir: {settings.media_dir}")
        print(f"   RSS file: {settings.rss_file}")
        
        if not settings.rss_file.exists():
            print("❌ RSS file not found!")
            return
        
        # Parse existing RSS
        tree = ET.parse(settings.rss_file)
        root = tree.getroot()
        channel = root.find('channel')
        
        if channel is None:
            print("❌ No channel found in RSS!")
            return
        
        # Find all items
        items = channel.findall('item')
        print(f"📖 Found {len(items)} episodes in feed")
        
        # Group episodes by base GUID (without _partN)
        episode_groups = {}
        for item in items:
            guid_elem = item.find('guid')
            if guid_elem is None:
                continue
            
            guid = guid_elem.text
            
            # Check if it's a part
            if '_part' in guid:
                base_guid = guid.split('_part')[0]
                part_num = int(guid.split('_part')[1])
            else:
                base_guid = guid
                part_num = 0
            
            if base_guid not in episode_groups:
                episode_groups[base_guid] = []
            episode_groups[base_guid].append((part_num, item, guid))
        
        print(f"📊 Found {len(episode_groups)} episode groups")
        
        # Process each group
        episodes_to_add = []
        
        for base_guid, parts in episode_groups.items():
            # Sort by part number
            parts.sort(key=lambda x: x[0])
            
            print(f"\n🎵 Processing: {base_guid}")
            
            # Check if it's a YouTube video or uploaded file
            first_item = parts[0][1]
            link_elem = first_item.find('link')
            is_youtube = link_elem is not None and 'youtube.com' in (link_elem.text or '')
            
            if is_youtube:
                print(f"   ⏭️ Skipping YouTube video")
                # Keep YouTube episodes as-is
                for part_num, item, guid in parts:
                    episodes_to_add.append(extract_episode_data(item, guid, settings, splitter))
                continue
            
            # Count actual media files
            actual_parts = []
            for part_num, item, guid in parts:
                media_file = settings.media_dir / f"{guid}.mp3"
                if media_file.exists():
                    actual_parts.append((part_num, item, guid, media_file))
                    print(f"   ✅ Found: {media_file.name}")
                else:
                    print(f"   ❌ Missing: {guid}.mp3")
            
            if not actual_parts:
                print(f"   ⚠️ No media files found, skipping")
                continue
            
            total_parts = len(actual_parts)
            print(f"   📁 Total parts: {total_parts}")
            
            # Get title from first part
            title_elem = first_item.find('title')
            base_title = title_elem.text if title_elem is not None else base_guid
            
            # Remove existing part suffix from title
            if '(Part' in base_title:
                base_title = base_title.split('(Part')[0].strip()
            
            # Get base pub_date
            pub_date_elem = first_item.find('pubDate')
            if pub_date_elem is not None and pub_date_elem.text:
                try:
                    base_pub_date = parsedate_to_datetime(pub_date_elem.text)
                except:
                    base_pub_date = datetime.now()
            else:
                base_pub_date = datetime.now()
            
            # Process each part with correct metadata
            for idx, (part_num, item, guid, media_file) in enumerate(actual_parts, 1):
                # Extract real duration
                try:
                    duration_seconds = splitter.get_audio_duration(media_file)
                    hours = duration_seconds // 3600
                    minutes = (duration_seconds % 3600) // 60
                    seconds = duration_seconds % 60
                    if hours > 0:
                        duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    else:
                        duration = f"{minutes:02d}:{seconds:02d}"
                    print(f"   ⏱️ {guid}: {duration}")
                except Exception as e:
                    duration = "01:00:00"
                    print(f"   ⚠️ Could not get duration for {guid}: {e}")
                
                # Create proper title
                if total_parts > 1:
                    title = f"{base_title} (Часть {idx}/{total_parts})"
                else:
                    title = base_title
                
                # Better description
                description = f"{base_title}"
                if total_parts > 1:
                    description += f" — Часть {idx} из {total_parts}"
                
                # Stagger pub dates for parts (2 minutes apart)
                pub_date = base_pub_date - timedelta(minutes=(total_parts - idx) * 2)
                
                # Get file info
                file_size = media_file.stat().st_size
                audio_url = f"{settings.media_base_url}/{media_file.name}"
                
                episode = EpisodeData(
                    guid=guid,
                    title=title,
                    link=settings.site_url,
                    description=description,
                    audio_url=audio_url,
                    audio_file_size=file_size,
                    audio_mime_type="audio/mpeg",
                    pub_date=pub_date,
                    duration=duration,
                    image_url=None,
                )
                
                episodes_to_add.append(episode)
        
        # Create new feed
        print(f"\n✍️ Creating new RSS feed with {len(episodes_to_add)} episodes...")
        
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
        
        fg = rss_manager.create_feed()
        
        for episode in episodes_to_add:
            rss_manager.add_episode(fg, episode)
            print(f"   ➕ {episode.title}")
        
        # Save
        rss_manager.save_feed(fg, settings.rss_file)
        
        # Also copy to docs
        docs_rss = settings.podcast_dir.parent / 'docs' / 'rss.xml'
        if docs_rss.parent.exists():
            import shutil
            shutil.copy(settings.rss_file, docs_rss)
            print(f"   📋 Copied to: {docs_rss}")
        
        print(f"\n✅ RSS feed fixed successfully!")
        print(f"📁 File: {settings.rss_file}")
        print(f"📝 Episodes: {len(episodes_to_add)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def extract_episode_data(item, guid, settings, splitter):
    """Extract episode data from XML item."""
    title_elem = item.find('title')
    link_elem = item.find('link')
    desc_elem = item.find('description')
    pub_date_elem = item.find('pubDate')
    enclosure_elem = item.find('enclosure')
    
    itunes_ns = '{http://www.itunes.com/dtds/podcast-1.0.dtd}'
    duration_elem = item.find(f'{itunes_ns}duration')
    image_elem = item.find(f'{itunes_ns}image')
    
    # Get duration from file if not in RSS
    duration = duration_elem.text if duration_elem is not None else '00:00'
    if duration == '00:00':
        media_file = settings.media_dir / f"{guid}.mp3"
        if media_file.exists():
            try:
                duration_seconds = splitter.get_audio_duration(media_file)
                hours = duration_seconds // 3600
                minutes = (duration_seconds % 3600) // 60
                seconds = duration_seconds % 60
                duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes:02d}:{seconds:02d}"
            except:
                pass
    
    # Get pub date
    pub_date = datetime.now()
    if pub_date_elem is not None and pub_date_elem.text:
        try:
            pub_date = parsedate_to_datetime(pub_date_elem.text)
        except:
            pass
    
    # Get file info
    if enclosure_elem is not None:
        audio_url = enclosure_elem.get('url', '')
        file_size = int(enclosure_elem.get('length', 0))
    else:
        audio_url = f"{settings.media_base_url}/{guid}.mp3"
        media_file = settings.media_dir / f"{guid}.mp3"
        file_size = media_file.stat().st_size if media_file.exists() else 0
    
    return EpisodeData(
        guid=guid,
        title=title_elem.text if title_elem is not None else guid,
        link=link_elem.text if link_elem is not None else '',
        description=desc_elem.text if desc_elem is not None else '',
        audio_url=audio_url,
        audio_file_size=file_size,
        audio_mime_type="audio/mpeg",
        pub_date=pub_date,
        duration=duration,
        image_url=image_elem.get('href') if image_elem is not None else None,
    )


if __name__ == '__main__':
    main()
