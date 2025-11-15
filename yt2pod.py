#!/usr/bin/env python3
"""
YouTube to Podcast Converter
Main script for converting YouTube videos to podcast episodes.
"""

import sys
from pathlib import Path
from utils.logger import setup_logger
from config import get_settings, ConfigurationError

# Setup logging
logger = setup_logger("yt2pod")


def main():
    """Main entry point for the YouTube to Podcast converter."""
    logger.info("YouTube to Podcast Converter v0.1.0")
    
    # Load and validate configuration
    try:
        settings = get_settings()
        settings.ensure_directories()
        logger.info(f"Configuration loaded successfully")
        logger.info(f"Site URL: {settings.site_url}")
        logger.info(f"Audio format: {settings.audio_format}")
    except ConfigurationError as e:
        logger.error(f"Configuration error:\n{e}")
        logger.error("\nPlease create a .env file or set environment variables.")
        logger.error("See .env.example for configuration template.")
        sys.exit(1)
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        logger.error("Usage: python yt2pod.py <youtube_url> [youtube_url2 ...]")
        sys.exit(1)
    
    urls = sys.argv[1:]
    logger.info(f"Processing {len(urls)} URL(s)")
    
    # Parse and validate URLs
    from utils.url_processor import process_urls
    
    parsed_urls = process_urls(urls)
    
    if not parsed_urls:
        logger.error("No valid YouTube URLs provided")
        sys.exit(1)
    
    logger.info(f"Successfully parsed {len(parsed_urls)} valid URL(s)")
    
    # Initialize downloader, RSS manager and splitter
    from utils.downloader import AudioDownloader
    from utils.rss_manager import RSSManager, EpisodeData
    from utils.audio_splitter import AudioSplitter
    
    downloader = AudioDownloader(
        output_dir=settings.media_dir,
        audio_format=settings.audio_format
    )
    
    splitter = AudioSplitter()
    
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
    
    # Load or create RSS feed
    fg = rss_manager.load_existing_feed(settings.rss_file)
    if fg is None:
        logger.info("Creating new RSS feed")
        fg = rss_manager.create_feed()
    else:
        logger.info("Loaded existing RSS feed")
    
    # Get existing episode GUIDs to avoid duplicates
    existing_guids = rss_manager.get_existing_guids(settings.rss_file)
    if existing_guids:
        logger.info(f"Found {len(existing_guids)} existing episode(s) in feed")
    
    # Process each video
    for parsed_url in parsed_urls:
        logger.info(f"\nProcessing video: {parsed_url.video_id}")
        logger.info(f"  URL: {parsed_url.original_url}")
        
        if parsed_url.is_playlist:
            logger.info(f"  Playlist ID: {parsed_url.playlist_id}")
            logger.warning("  Note: Playlist processing not yet implemented (v1 focuses on individual videos)")
        
        try:
            # Download audio with metadata
            logger.info(f"  Downloading audio...")
            audio_file, metadata = downloader.download_with_metadata(
                url=parsed_url.original_url,
                video_id=parsed_url.video_id
            )
            
            logger.info(f"  ✓ Downloaded: {audio_file.name}")
            logger.info(f"  Title: {metadata.title}")
            logger.info(f"  Duration: {metadata.formatted_duration}")
            logger.info(f"  Uploader: {metadata.uploader}")
            
            # Check if audio needs to be split (videos > 1 hour)
            audio_files_to_process = []
            
            if splitter.should_split(metadata.duration):
                logger.info(f"  Video duration ({metadata.formatted_duration}) exceeds 1 hour, splitting into parts...")
                
                try:
                    segments = splitter.split_audio(audio_file)
                    logger.info(f"  ✓ Split into {len(segments)} parts")
                    
                    audio_files_to_process = segments
                    
                    # Remove original file after successful split
                    if audio_file.exists():
                        audio_file.unlink()
                        logger.info(f"  ✓ Removed original file")
                        
                except Exception as e:
                    logger.error(f"  ✗ Failed to split audio: {e}")
                    logger.warning(f"  Using full video as single episode")
                    audio_files_to_process = [{'file': audio_file, 'part': None}]
            else:
                # Video is short enough, process as single episode
                audio_files_to_process = [{'file': audio_file, 'part': None}]
            
            # Process each audio file (either segments or single file)
            episodes_added = 0
            
            for item in audio_files_to_process:
                # Handle both segment objects and simple dict
                if isinstance(item, dict):
                    # Simple file (no splitting)
                    current_file = item['file']
                    part_number = None
                    total_parts = 1
                    segment_duration = None
                else:
                    # Segment object
                    current_file = item.file_path
                    part_number = item.part_number
                    total_parts = item.total_parts
                    segment_duration = item.formatted_duration
                
                # Generate unique GUID for each part
                if part_number:
                    episode_guid = f"{metadata.video_id}_part{part_number}"
                    episode_title = f"{metadata.title} (Part {part_number}/{total_parts})"
                else:
                    episode_guid = metadata.video_id
                    episode_title = metadata.title
                
                # Skip if already exists
                if episode_guid in existing_guids:
                    logger.warning(f"  Episode {episode_guid} already exists in feed, skipping")
                    continue
                
                # Add episode to RSS feed
                audio_url = f"{settings.media_base_url}/{current_file.name}"
                file_size = current_file.stat().st_size
                mime_type = "audio/mp4" if settings.audio_format == "m4a" else "audio/mpeg"
                
                episode = EpisodeData(
                    guid=episode_guid,
                    title=episode_title,
                    link=metadata.webpage_url or parsed_url.normalized_url,
                    description=metadata.description or metadata.title,
                    audio_url=audio_url,
                    audio_file_size=file_size,
                    audio_mime_type=mime_type,
                    pub_date=metadata.pub_date,
                    duration=segment_duration or metadata.formatted_duration,
                    image_url=metadata.thumbnail_url,
                )
                
                rss_manager.add_episode(fg, episode)
                existing_guids.add(episode_guid)
                episodes_added += 1
                logger.info(f"  ✓ Added to RSS feed: {episode_title}")
            
            if episodes_added == 0:
                logger.warning(f"  No new episodes added (already in feed)")
            
        except Exception as e:
            logger.error(f"  ✗ Failed to process video: {e}")
            continue
    
    # Save RSS feed
    rss_manager.save_feed(fg, settings.rss_file, max_items=settings.feed_max_items)
    
    logger.info(f"\n✓ Completed processing {len(parsed_urls)} video(s)")
    logger.info(f"✓ RSS feed saved to: {settings.rss_file}")
    logger.info(f"✓ Feed URL: {settings.site_url}/rss.xml")


if __name__ == "__main__":
    main()
