#!/usr/bin/env python3
"""
Fix media URLs in RSS feed to point to Railway domain.
"""

import sys
from pathlib import Path
from config import get_settings
from utils.rss_manager import RSSManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_media_urls():
    """Update media URLs in RSS feed."""
    try:
        settings = get_settings()
        
        logger.info(f"Loading RSS feed from: {settings.rss_file}")
        
        # Load existing feed
        rss_manager = RSSManager(
            site_url=settings.site_url,
            media_base_url=settings.media_base_url,
            title=settings.podcast_title,
            description=settings.podcast_description,
            author=settings.podcast_author,
            language=settings.podcast_language,
            category=settings.podcast_category,
        )
        
        fg = rss_manager.load_existing_feed(settings.rss_file)
        
        if fg is None:
            logger.error("No RSS feed found")
            return False
        
        # Update media URLs in all entries
        updated_count = 0
        for entry in fg.episodes():
            for enclosure in entry.enclosure():
                old_url = enclosure.get('url', '')
                # Extract filename from old URL
                filename = old_url.split('/')[-1]
                # Build new URL
                new_url = f"{settings.media_base_url}/{filename}"
                
                if old_url != new_url:
                    enclosure.set('url', new_url)
                    updated_count += 1
                    logger.info(f"Updated: {filename}")
                    logger.info(f"  From: {old_url}")
                    logger.info(f"  To: {new_url}")
        
        if updated_count > 0:
            # Save updated feed
            rss_manager.save_feed(fg, settings.rss_file)
            logger.info(f"✅ Updated {updated_count} media URLs")
            logger.info(f"RSS feed saved to: {settings.rss_file}")
            return True
        else:
            logger.info("No URLs needed updating")
            return True
            
    except Exception as e:
        logger.error(f"Failed to fix media URLs: {e}")
        return False


if __name__ == '__main__':
    success = fix_media_urls()
    sys.exit(0 if success else 1)
