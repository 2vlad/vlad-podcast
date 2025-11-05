#!/usr/bin/env python3
"""
Convert all existing M4A files to MP3 and update RSS feed.
This script ensures maximum compatibility with all podcast players, including Light Phone.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.audio_converter import convert_to_mp3, AudioConverterError
from utils.rss_manager import get_mime_type_from_filename
from config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def convert_all_to_mp3():
    """Convert all M4A files in media directory to MP3."""
    settings = get_settings()
    media_dir = settings.media_dir
    
    if not media_dir.exists():
        logger.error(f"Media directory not found: {media_dir}")
        return
    
    # Find all M4A files
    m4a_files = list(media_dir.glob('*.m4a')) + list(media_dir.glob('*.mp4'))
    
    if not m4a_files:
        logger.info("No M4A/MP4 files found to convert")
        return
    
    logger.info(f"Found {len(m4a_files)} files to convert")
    logger.info("=" * 60)
    
    converted_count = 0
    failed_count = 0
    
    for m4a_file in m4a_files:
        try:
            logger.info(f"\n📁 Processing: {m4a_file.name}")
            logger.info(f"   Size: {m4a_file.stat().st_size / 1024 / 1024:.2f} MB")
            
            # Convert to MP3
            mp3_file = convert_to_mp3(
                m4a_file,
                quality=2,  # ~190kbps VBR
                keep_original=False  # Remove M4A after conversion
            )
            
            logger.info(f"   ✅ Converted: {mp3_file.name}")
            logger.info(f"   New size: {mp3_file.stat().st_size / 1024 / 1024:.2f} MB")
            logger.info(f"   MIME type: {get_mime_type_from_filename(mp3_file.name)}")
            
            converted_count += 1
            
        except AudioConverterError as e:
            logger.error(f"   ❌ Failed: {e}")
            failed_count += 1
        except Exception as e:
            logger.error(f"   ❌ Unexpected error: {e}")
            failed_count += 1
    
    logger.info("\n" + "=" * 60)
    logger.info(f"✅ Conversion complete!")
    logger.info(f"   Converted: {converted_count}")
    logger.info(f"   Failed: {failed_count}")
    logger.info(f"   Total: {len(m4a_files)}")
    
    if converted_count > 0:
        logger.info("\n⚠️  IMPORTANT: You need to regenerate the RSS feed!")
        logger.info("   Run: python regenerate_feed.py")


if __name__ == '__main__':
    try:
        convert_all_to_mp3()
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Conversion interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        sys.exit(1)
