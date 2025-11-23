#!/usr/bin/env python3
"""
Web interface for YouTube to Podcast Converter
Minimal Flask server with Apple-style UI
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
import threading
import logging
from datetime import datetime, timezone
import hashlib
import os
from werkzeug.utils import secure_filename

from config import get_settings, ConfigurationError
from utils.logger import setup_logger
from utils.url_processor import process_urls
from utils.downloader import AudioDownloader
from utils.rss_manager import RSSManager, EpisodeData, get_mime_type_from_filename
from utils.github_publisher import GitHubPublisher
from utils.audio_splitter import AudioSplitter
from utils.transcript_manager import TranscriptManager

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# File upload configuration
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
ALLOWED_EXTENSIONS = {'mp3', 'mp4', 'm4a'}

logger = setup_logger("web")

# Job status tracking
jobs = {}
job_id_counter = 0
job_lock = threading.Lock()

# Transcription manager (lazy init to avoid early config issues)
_transcript_manager = None


def get_transcript_manager() -> TranscriptManager:
    global _transcript_manager
    if _transcript_manager is None:
        settings = get_settings()
        tm = TranscriptManager(settings.podcast_dir, api_key=settings.assemblyai_api_key)
        _set_transcript_manager(tm)
    return _transcript_manager


def _set_transcript_manager(tm: TranscriptManager):
    global _transcript_manager
    _transcript_manager = tm


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_upload_job(job_id: int, file_path: Path, original_filename: str, title: str = None, description: str = None):
    """Background job to process an uploaded audio/video file."""
    global jobs
    
    try:
        logger.info(f"[Job {job_id}] Starting upload processing for: {original_filename}")
        
        # Check if file exists and log size
        if not file_path.exists():
            logger.error(f"[Job {job_id}] File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size_bytes = file_path.stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)
        logger.info(f"[Job {job_id}] File size: {file_size_mb:.2f} MB ({file_size_bytes} bytes)")
        logger.info(f"[Job {job_id}] File path: {file_path}")
        logger.info(f"[Job {job_id}] Original filename: {original_filename}")
        
        jobs[job_id]['status'] = 'processing'
        jobs[job_id]['message'] = 'Processing uploaded file...'
        jobs[job_id]['progress'] = {'status': 'processing', 'percent': 0}
        
        settings = get_settings()
        logger.info(f"[Job {job_id}] Settings loaded - Media dir: {settings.media_dir}, Audio format: {settings.audio_format}")
        
        # Ensure directories exist before processing
        settings.ensure_directories()
        logger.info(f"[Job {job_id}] Directories verified")
        
        # Generate unique ID from file content
        logger.info(f"[Job {job_id}] Generating file hash...")
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()[:11]
        
        logger.info(f"[Job {job_id}] Generated file hash: {file_hash}")
        jobs[job_id]['video_id'] = file_hash
        
        # Determine file extension
        ext = file_path.suffix.lower()
        target_format = settings.audio_format
        logger.info(f"[Job {job_id}] File extension: {ext}, Target format: {target_format}")
        
        # Convert to target format if needed
        if ext == '.mp4':
            logger.info(f"[Job {job_id}] MP4 file detected, starting conversion to {target_format}")
            jobs[job_id]['message'] = 'Converting MP4 to audio...'
            jobs[job_id]['progress'] = {'status': 'converting', 'percent': 50}
            
            # Use ffmpeg to convert
            output_file = settings.media_dir / f"{file_hash}.{target_format}"
            logger.info(f"[Job {job_id}] Output file will be: {output_file}")
            
            import subprocess
            
            cmd = [
                'ffmpeg',
                '-loglevel', 'info',  # Show more detailed logs for debugging
                '-i', str(file_path),
                '-vn',  # No video
                '-acodec', 'aac' if target_format == 'm4a' else 'libmp3lame',
                '-q:a', '2',  # Quality
                str(output_file)
            ]
            
            logger.info(f"[Job {job_id}] FFmpeg command: {' '.join(cmd)}")
            logger.info(f"[Job {job_id}] Starting FFmpeg conversion...")
            
            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                logger.info(f"[Job {job_id}] FFmpeg conversion successful")
                logger.debug(f"[Job {job_id}] FFmpeg stdout: {result.stdout}")
                
                # Check output file was created
                if not output_file.exists():
                    logger.error(f"[Job {job_id}] Output file was not created: {output_file}")
                    raise FileNotFoundError(f"FFmpeg did not create output file: {output_file}")
                
                output_size_mb = output_file.stat().st_size / (1024 * 1024)
                logger.info(f"[Job {job_id}] Converted file size: {output_size_mb:.2f} MB")
                
                # Remove original file
                file_path.unlink()
                logger.info(f"[Job {job_id}] Removed original MP4 file: {file_path}")
                audio_file = output_file
                
            except subprocess.CalledProcessError as e:
                logger.error(f"[Job {job_id}] FFmpeg conversion failed with code {e.returncode}")
                logger.error(f"[Job {job_id}] FFmpeg stderr: {e.stderr}")
                logger.error(f"[Job {job_id}] FFmpeg stdout: {e.stdout}")
                logger.warning(f"[Job {job_id}] Falling back to using original MP4 file")
                
                # If conversion fails, just rename the file
                audio_file = file_path.rename(settings.media_dir / f"{file_hash}{ext}")
                logger.info(f"[Job {job_id}] Renamed original file to: {audio_file}")
        else:
            # MP3/M4A files - just rename
            logger.info(f"[Job {job_id}] Audio file detected ({ext}), renaming without conversion")
            audio_file = file_path.rename(settings.media_dir / f"{file_hash}{ext}")
            logger.info(f"[Job {job_id}] Renamed file to: {audio_file}")
        
        jobs[job_id]['message'] = 'Extracting metadata...'
        jobs[job_id]['progress'] = {'status': 'metadata', 'percent': 75}
        
        logger.info(f"[Job {job_id}] Extracting metadata from audio file")
        
        # Get file size
        file_size = audio_file.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        logger.info(f"[Job {job_id}] Final audio file size: {file_size_mb:.2f} MB ({file_size} bytes)")
        
        # Extract duration using ffprobe
        splitter = AudioSplitter()
        audio_duration = splitter.get_audio_duration(audio_file)
        
        # Format duration as HH:MM:SS
        hours = audio_duration // 3600
        minutes = (audio_duration % 3600) // 60
        seconds = audio_duration % 60
        formatted_duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes:02d}:{seconds:02d}"
        
        logger.info(f"[Job {job_id}] Audio duration: {formatted_duration} ({audio_duration} seconds)")
        
        # Use provided title or filename
        if not title:
            title = Path(original_filename).stem
        
        if not description:
            description = f"Uploaded audio: {original_filename}"
        
        logger.info(f"[Job {job_id}] Episode title: {title}")
        logger.info(f"[Job {job_id}] Episode description: {description[:100]}...")
        
        jobs[job_id]['title'] = title
        jobs[job_id]['duration'] = formatted_duration
        
        # Check if audio needs to be split (files > 1 hour)
        audio_files_to_process = []
        
        if splitter.should_split(audio_duration):
            logger.info(f"[Job {job_id}] Audio is {formatted_duration}, splitting into parts...")
            jobs[job_id]['message'] = f'Audio is {formatted_duration}, splitting into parts...'
            jobs[job_id]['progress'] = {'status': 'splitting', 'percent': 80}
            
            try:
                segments = splitter.split_audio(audio_file)
                logger.info(f"[Job {job_id}] Split audio into {len(segments)} parts")
                
                # Store segment info for RSS generation
                audio_files_to_process = segments
                
                # Remove original file after successful split
                if audio_file.exists():
                    audio_file.unlink()
                    logger.info(f"[Job {job_id}] Removed original file: {audio_file}")
                
                jobs[job_id]['message'] = f'Split into {len(segments)} episodes'
                jobs[job_id]['split_parts'] = len(segments)
                
            except Exception as e:
                logger.error(f"[Job {job_id}] Failed to split audio: {e}", exc_info=True)
                # If splitting fails, use original file
                audio_files_to_process = [{'file': audio_file, 'part': None, 'duration': formatted_duration}]
                jobs[job_id]['message'] = 'Split failed, using full audio'
        else:
            # Audio is short enough, process as single episode
            logger.info(f"[Job {job_id}] Audio duration {formatted_duration} is under 1 hour, no splitting needed")
            audio_files_to_process = [{'file': audio_file, 'part': None, 'duration': formatted_duration}]
        
        jobs[job_id]['message'] = 'Updating RSS feed...'
        jobs[job_id]['progress'] = {'status': 'feed', 'percent': 90}
        logger.info(f"[Job {job_id}] Starting RSS feed update")
        
        # Update RSS
        logger.info(f"[Job {job_id}] Creating RSS manager")
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
        logger.info(f"[Job {job_id}] RSS manager created - Site URL: {settings.site_url}, Media base URL: {settings.media_base_url}")
        
        logger.info(f"[Job {job_id}] Loading existing RSS feed from: {settings.rss_file}")
        fg = rss_manager.load_existing_feed(settings.rss_file)
        if fg is None:
            logger.info(f"[Job {job_id}] No existing feed found, creating new feed")
            fg = rss_manager.create_feed()
        else:
            logger.info(f"[Job {job_id}] Existing feed loaded successfully")
        
        logger.info(f"[Job {job_id}] Getting existing episode GUIDs")
        existing_guids = rss_manager.get_existing_guids(settings.rss_file)
        logger.info(f"[Job {job_id}] Found {len(existing_guids)} existing episodes in feed")
        
        # Process each audio file (either segments or single file)
        episodes_added = 0
        
        for item in audio_files_to_process:
            # Handle both segment objects and simple dict
            if isinstance(item, dict):
                # Simple file (no splitting)
                current_file = item['file']
                part_number = None
                total_parts = 1
                segment_duration = item.get('duration', formatted_duration)
            else:
                # Segment object
                current_file = item.file_path
                part_number = item.part_number
                total_parts = item.total_parts
                segment_duration = item.formatted_duration
            
            # Generate unique GUID for each part
            if part_number:
                episode_guid = f"{file_hash}_part{part_number}"
                episode_title = f"{title} (Part {part_number}/{total_parts})"
            else:
                episode_guid = file_hash
                episode_title = title
            
            # Skip if already exists
            if episode_guid in existing_guids:
                logger.info(f"[Job {job_id}] Episode {episode_guid} already in feed, skipping")
                continue
            
            # Create episode
            audio_url = f"{settings.media_base_url}/{current_file.name}"
            current_file_size = current_file.stat().st_size
            mime_type = get_mime_type_from_filename(current_file.name)
            
            logger.info(f"[Job {job_id}] Adding episode: {episode_title}")
            logger.info(f"[Job {job_id}]   GUID: {episode_guid}")
            logger.info(f"[Job {job_id}]   Audio URL: {audio_url}")
            logger.info(f"[Job {job_id}]   Duration: {segment_duration}")
            logger.info(f"[Job {job_id}]   File size: {current_file_size / (1024 * 1024):.2f} MB")
            
            episode = EpisodeData(
                guid=episode_guid,
                title=episode_title,
                link=settings.site_url,  # No external link for uploads
                description=description if not part_number else f"{description} (Part {part_number}/{total_parts})",
                audio_url=audio_url,
                audio_file_size=current_file_size,
                audio_mime_type=mime_type,
                pub_date=datetime.now(timezone.utc),
                duration=segment_duration or formatted_duration,  # Fallback to ensure duration is always set
                image_url=None,  # No thumbnail for uploads
            )
            
            try:
                rss_manager.add_episode(fg, episode)
                existing_guids.add(episode_guid)
                episodes_added += 1
                logger.info(f"[Job {job_id}] Episode {episode_guid} added successfully")
            except Exception as e:
                logger.error(f"[Job {job_id}] Failed to add episode {episode_guid}: {e}", exc_info=True)
                raise
        
        if episodes_added == 0:
            logger.warning(f"[Job {job_id}] No new episodes added (all already in feed)")
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['message'] = 'Already in feed'
            jobs[job_id]['duplicate'] = True
            return
        
        logger.info(f"[Job {job_id}] Added {episodes_added} episode(s) to feed")
        logger.info(f"[Job {job_id}] Saving RSS feed to: {settings.rss_file}")
        try:
            rss_manager.save_feed(fg, settings.rss_file, max_items=settings.feed_max_items)
            logger.info(f"[Job {job_id}] RSS feed saved successfully")
        except Exception as e:
            logger.error(f"[Job {job_id}] Failed to save RSS feed: {e}", exc_info=True)
            raise
        
        # Auto-publish to GitHub Pages if configured
        if settings.auto_publish == 'github':
            jobs[job_id]['message'] = 'Uploading to GitHub Releases...'
            jobs[job_id]['progress'] = {'status': 'uploading', 'percent': 90}
            
            try:
                publisher = GitHubPublisher(
                    repo_path=settings.base_dir,
                    branch=settings.github_branch
                )
                
                # Upload all audio files to GitHub Releases
                uploaded_count = 0
                for item in audio_files_to_process:
                    current_file = item.file_path if hasattr(item, 'file_path') else item['file']
                    
                    jobs[job_id]['message'] = f'Uploading {current_file.name} to GitHub Releases...'
                    upload_success = publisher.upload_to_release(current_file)
                
                    if upload_success:
                        uploaded_count += 1
                        logger.info(f"[Job {job_id}] Uploaded {current_file.name} to GitHub Releases ({uploaded_count}/{len(audio_files_to_process)})")
                
                if uploaded_count > 0:
                    logger.info(f"[Job {job_id}] Uploaded {uploaded_count} file(s) to GitHub Releases")
                    
                    # Update RSS with GitHub Releases URLs
                    jobs[job_id]['message'] = 'Updating RSS feed with GitHub URLs...'
                    jobs[job_id]['progress'] = {'status': 'updating_rss', 'percent': 95}
                    
                    # Update audio URLs in RSS
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(settings.rss_file)
                    root = tree.getroot()
                    channel = root.find('channel')
                    
                    if channel:
                        for item_elem in channel.findall('item'):
                            guid_elem = item_elem.find('guid')
                            if guid_elem is not None:
                                # Check if this is one of our episodes
                                if guid_elem.text == file_hash or guid_elem.text.startswith(f"{file_hash}_part"):
                                    enclosure = item_elem.find('enclosure')
                                    if enclosure is not None:
                                        # Extract filename from current URL
                                        current_url = enclosure.get('url', '')
                                        filename = current_url.split('/')[-1]
                                        # Replace with GitHub Releases URL
                                        github_url = f"https://github.com/{settings.github_repo}/releases/download/media-files/{filename}"
                                        enclosure.set('url', github_url)
                        
                        tree.write(settings.rss_file, encoding='utf-8', xml_declaration=True)
                        logger.info(f"[Job {job_id}] Updated {uploaded_count} audio URL(s) to GitHub Releases")
                    
                    # Publish RSS to GitHub Pages
                    jobs[job_id]['message'] = 'Publishing to GitHub Pages...'
                    jobs[job_id]['progress'] = {'status': 'publishing', 'percent': 98}
                    
                    episode_title_msg = f"{title} ({episodes_added} episode{'s' if episodes_added > 1 else ''})"
                    publish_success = publisher.publish(
                        episode_title=episode_title_msg,
                        rss_file=settings.rss_file,
                        patterns=["docs/"]
                    )
                    
                    if publish_success:
                        pages_url = f"https://2vlad.github.io/vlad-podcast/rss.xml"
                        jobs[job_id]['message'] = f'Published to GitHub Pages!'
                        jobs[job_id]['pages_url'] = pages_url
                        logger.info(f"Published uploaded file to GitHub Pages: {pages_url}")
                    else:
                        jobs[job_id]['message'] = 'Upload completed (RSS publish failed)'
                        logger.warning("RSS publish failed, file uploaded to GitHub Releases")
                else:
                    jobs[job_id]['message'] = 'Upload completed (GitHub upload failed)'
                    logger.warning("GitHub Releases upload failed, files saved locally")
            except Exception as e:
                jobs[job_id]['message'] = f'Upload completed (publish error: {str(e)})'
                logger.error(f"GitHub publish error: {e}")
        
        jobs[job_id]['status'] = 'completed'
        if 'message' not in jobs[job_id] or 'Publishing' in jobs[job_id]['message']:
            jobs[job_id]['message'] = 'Upload completed successfully!'
        jobs[job_id]['progress'] = {'status': 'completed', 'percent': 100}
        
        logger.info(f"[Job {job_id}] ✅ Successfully processed uploaded file: {original_filename}")
        logger.info(f"[Job {job_id}] Episode ID: {file_hash}")
        logger.info(f"[Job {job_id}] Episode title: {title}")
        logger.info(f"[Job {job_id}] Episodes created: {episodes_added}")
        if episodes_added > 1:
            logger.info(f"[Job {job_id}] Audio was split into {episodes_added} parts (>1 hour)")
        logger.info(f"[Job {job_id}] Job completed successfully")
        
    except Exception as e:
        logger.error(f"[Job {job_id}] ❌ Failed to process upload: {e}", exc_info=True)
        logger.error(f"[Job {job_id}] Original filename: {original_filename}")
        logger.error(f"[Job {job_id}] File path: {file_path}")
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['message'] = f'Error: {str(e)}'
        jobs[job_id]['progress'] = {'status': 'error', 'percent': 0}


def process_video_job(job_id: int, url: str):
    """Background job to process a single video URL."""
    global jobs
    
    def progress_callback(progress_data):
        """Update job progress."""
        jobs[job_id]['progress'] = progress_data
        if progress_data['status'] == 'downloading':
            percent = progress_data['percent']
            speed = progress_data['speed']
            eta = progress_data['eta']
            jobs[job_id]['message'] = f'Downloading: {percent:.1f}% ({speed}, ETA: {eta})'
        elif progress_data['status'] == 'converting':
            jobs[job_id]['message'] = 'Converting to audio...'
    
    try:
        jobs[job_id]['status'] = 'processing'
        jobs[job_id]['message'] = 'Validating URL...'
        jobs[job_id]['progress'] = {'status': 'starting', 'percent': 0}
        
        # Load settings
        settings = get_settings()
        # Ensure directories exist before processing
        settings.ensure_directories()
        
        # Parse URL
        parsed_urls = process_urls([url])
        if not parsed_urls:
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['message'] = 'Invalid YouTube URL'
            return
        
        parsed_url = parsed_urls[0]
        jobs[job_id]['video_id'] = parsed_url.video_id
        jobs[job_id]['message'] = 'Starting download...'
        
        # Download with progress tracking
        downloader = AudioDownloader(
            output_dir=settings.media_dir,
            audio_format=settings.audio_format,
            progress_callback=progress_callback
        )
        
        audio_file, metadata = downloader.download_with_metadata(
            url=parsed_url.original_url,
            video_id=parsed_url.video_id
        )
        
        jobs[job_id]['message'] = 'Checking video duration...'
        jobs[job_id]['title'] = metadata.title
        jobs[job_id]['duration'] = metadata.formatted_duration
        
        # Check if audio needs to be split (videos > 1 hour)
        splitter = AudioSplitter()
        audio_files_to_process = []
        
        if splitter.should_split(metadata.duration):
            jobs[job_id]['message'] = f'Video is {metadata.formatted_duration}, splitting into parts...'
            jobs[job_id]['progress'] = {'status': 'splitting', 'percent': 85}
            
            try:
                segments = splitter.split_audio(audio_file)
                logger.info(f"Split video into {len(segments)} parts")
                
                # Store segment info for RSS generation
                audio_files_to_process = segments
                
                # Remove original file after successful split
                if audio_file.exists():
                    audio_file.unlink()
                    logger.info(f"Removed original file: {audio_file}")
                
                jobs[job_id]['message'] = f'Split into {len(segments)} episodes'
                jobs[job_id]['split_parts'] = len(segments)
                
            except Exception as e:
                logger.error(f"Failed to split audio: {e}")
                # If splitting fails, use original file
                audio_files_to_process = [{'file': audio_file, 'part': None}]
                jobs[job_id]['message'] = 'Split failed, using full video'
        else:
            # Video is short enough, process as single episode
            audio_files_to_process = [{'file': audio_file, 'part': None}]
        
        # Update RSS
        jobs[job_id]['message'] = 'Updating RSS feed...'
        jobs[job_id]['progress'] = {'status': 'feed', 'percent': 90}
        
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
        
        fg = rss_manager.load_existing_feed(settings.rss_file)
        if fg is None:
            fg = rss_manager.create_feed()
        
        existing_guids = rss_manager.get_existing_guids(settings.rss_file)
        
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
                logger.info(f"Episode {episode_guid} already in feed, skipping")
                continue
            
            # Create episode
            audio_url = f"{settings.media_base_url}/{current_file.name}"
            file_size = current_file.stat().st_size
            mime_type = get_mime_type_from_filename(current_file.name)
            
            episode = EpisodeData(
                guid=episode_guid,
                title=episode_title,
                link=metadata.webpage_url or parsed_url.normalized_url,
                description=metadata.description or metadata.title,
                audio_url=audio_url,
                audio_file_size=file_size,
                audio_mime_type=mime_type,
                pub_date=datetime.now(timezone.utc),
                duration=segment_duration or metadata.formatted_duration,
                image_url=metadata.thumbnail_url,
            )
            
            rss_manager.add_episode(fg, episode)
            existing_guids.add(episode_guid)
            episodes_added += 1
            logger.info(f"Added episode: {episode_title}")
        
        if episodes_added == 0:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['message'] = 'Already in feed'
            jobs[job_id]['duplicate'] = True
            return
        
        # Save RSS with all episodes
        rss_manager.save_feed(fg, settings.rss_file, max_items=settings.feed_max_items)
        logger.info(f"Added {episodes_added} episode(s) to RSS feed")
        
        # Auto-publish to GitHub Pages if configured
        if settings.auto_publish == 'github':
            jobs[job_id]['message'] = 'Publishing to GitHub Pages...'
            jobs[job_id]['progress'] = {'status': 'publishing', 'percent': 95}
            
            try:
                publisher = GitHubPublisher(
                    repo_path=settings.base_dir,
                    branch=settings.github_branch
                )
                
                # Upload all audio files to GitHub Releases
                uploaded_count = 0
                for item in audio_files_to_process:
                    current_file = item.file_path if hasattr(item, 'file_path') else item['file']
                    
                    jobs[job_id]['message'] = f'Uploading {current_file.name} to GitHub Releases...'
                    upload_success = publisher.upload_to_release(current_file)
                    
                    if upload_success:
                        uploaded_count += 1
                        logger.info(f"Uploaded {current_file.name} to GitHub Releases")
                
                if uploaded_count > 0:
                    # Update RSS with GitHub Releases URLs
                    jobs[job_id]['message'] = 'Updating RSS with GitHub URLs...'
                    jobs[job_id]['progress'] = {'status': 'updating_rss', 'percent': 97}
                    
                    # Re-load RSS and update audio URLs
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(settings.rss_file)
                    root = tree.getroot()
                    channel = root.find('channel')
                    
                    if channel:
                        for item_elem in channel.findall('item'):
                            guid_elem = item_elem.find('guid')
                            if guid_elem is not None:
                                # Check if this is one of our episodes
                                if guid_elem.text.startswith(metadata.video_id):
                                    enclosure = item_elem.find('enclosure')
                                    if enclosure is not None:
                                        # Extract filename from current URL
                                        current_url = enclosure.get('url', '')
                                        filename = current_url.split('/')[-1]
                                        # Replace with GitHub Releases URL
                                        github_url = f"https://github.com/{settings.github_repo}/releases/download/media-files/{filename}"
                                        enclosure.set('url', github_url)
                        
                        tree.write(settings.rss_file, encoding='utf-8', xml_declaration=True)
                        logger.info(f"Updated {uploaded_count} audio URL(s) to GitHub Releases")
                
                # Publish RSS to GitHub Pages
                jobs[job_id]['message'] = 'Publishing RSS to GitHub Pages...'
                jobs[job_id]['progress'] = {'status': 'publishing', 'percent': 99}
                
                episode_title = f"{metadata.title} ({episodes_added} episode{'s' if episodes_added > 1 else ''})"
                publish_success = publisher.publish(
                    episode_title=episode_title,
                    rss_file=settings.rss_file,
                    patterns=["docs/"]
                )
                
                if publish_success:
                    pages_url = f"https://2vlad.github.io/vlad-podcast/rss.xml"
                    jobs[job_id]['message'] = f'Published {episodes_added} episode(s) to GitHub Pages!'
                    jobs[job_id]['pages_url'] = pages_url
                    logger.info(f"Published to GitHub Pages: {pages_url}")
                else:
                    jobs[job_id]['message'] = 'GitHub publish failed (saved locally)'
                    logger.warning("GitHub publish failed, files saved locally")
            except Exception as e:
                jobs[job_id]['message'] = f'Publish error: {str(e)}'
                logger.error(f"GitHub publish error: {e}")
        
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['message'] = jobs[job_id].get('message', 'Ready to upload')
        jobs[job_id]['file_path'] = str(audio_file)
        jobs[job_id]['file_name'] = audio_file.name
        jobs[job_id]['file_size'] = f"{file_size / 1024 / 1024:.1f} MB"
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['message'] = str(e)


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/api/process', methods=['POST'])
def process_url():
    """Process a YouTube URL."""
    global job_id_counter, jobs
    
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    # Create job
    with job_lock:
        job_id_counter += 1
        job_id = job_id_counter
        
        jobs[job_id] = {
            'id': job_id,
            'url': url,
            'status': 'pending',
            'message': 'Starting...',
            'created_at': datetime.now().isoformat(),
        }
    
    # Start background processing
    thread = threading.Thread(target=process_video_job, args=(job_id, url))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'status': 'pending'
    })


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload and process an audio/video file."""
    global job_id_counter, jobs
    
    logger.info("=" * 80)
    logger.info("📤 New file upload request received")
    
    # Check if file was uploaded
    if 'file' not in request.files:
        logger.error("No file provided in request")
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        logger.error("Empty filename provided")
        return jsonify({'error': 'Empty filename'}), 400
    
    logger.info(f"Upload filename: {file.filename}")
    
    if not allowed_file(file.filename):
        logger.error(f"Invalid file type: {file.filename}. Allowed: {ALLOWED_EXTENSIONS}")
        return jsonify({'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    # Get optional metadata
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    
    logger.info(f"Upload metadata - Title: {title or '(auto)'}, Description: {description or '(auto)'}")
    
    try:
        settings = get_settings()
        
        # Create temp directory if it doesn't exist
        temp_dir = settings.podcast_dir / 'temp'
        temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Temp directory: {temp_dir}")
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = temp_dir / filename
        
        logger.info(f"Saving file to: {temp_path}")
        file.save(str(temp_path))
        
        # Check saved file size
        saved_size = temp_path.stat().st_size
        saved_size_mb = saved_size / (1024 * 1024)
        logger.info(f"File saved successfully - Size: {saved_size_mb:.2f} MB ({saved_size} bytes)")
        
        # Create job
        with job_lock:
            job_id_counter += 1
            job_id = job_id_counter
            
            jobs[job_id] = {
                'id': job_id,
                'filename': filename,
                'status': 'pending',
                'message': 'File uploaded, processing...',
                'created_at': datetime.now().isoformat(),
            }
            
            logger.info(f"Created job {job_id} for file: {filename}")
        
        # Start background processing
        logger.info(f"Starting background processing thread for job {job_id}")
        thread = threading.Thread(
            target=process_upload_job,
            args=(job_id, temp_path, filename, title or None, description or None)
        )
        thread.daemon = True
        thread.start()
        logger.info(f"Background thread started for job {job_id}")
        
        response_data = {
            'job_id': job_id,
            'status': 'pending',
            'filename': filename
        }
        logger.info(f"Returning response: {response_data}")
        logger.info("=" * 80)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/status/<int:job_id>')
def get_status(job_id):
    """Get job status."""
    job = jobs.get(job_id)
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(job)


@app.route('/api/config')
def get_config():
    """Get current configuration."""
    try:
        settings = get_settings()
        return jsonify({
            'podcast_title': settings.podcast_title,
            'audio_format': settings.audio_format,
            'site_url': settings.site_url,
        })
    except ConfigurationError as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/episodes')
def get_episodes():
    """Get list of episodes from RSS feed."""
    try:
        settings = get_settings()
        tm = get_transcript_manager()
        
        # Check if RSS file exists
        if not settings.rss_file.exists():
            return jsonify({'episodes': []})
        
        # Parse RSS feed
        from feedgen.feed import FeedGenerator
        fg = FeedGenerator()
        fg.load_extension('podcast')
        
        with open(settings.rss_file, 'r', encoding='utf-8') as f:
            import xml.etree.ElementTree as ET
            tree = ET.parse(f)
            root = tree.getroot()
            
            episodes = []
            channel = root.find('channel')
            
            if channel is not None:
                for item in channel.findall('item'):
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    pub_date_elem = item.find('pubDate')
                    duration_elem = item.find('{http://www.itunes.com/dtds/podcast-1.0.dtd}duration')
                    enclosure_elem = item.find('enclosure')
                    guid_elem = item.find('guid')
                    
                    episode = {
                        'title': title_elem.text if title_elem is not None else 'Unknown',
                        'link': link_elem.text if link_elem is not None else '',
                        'pub_date': pub_date_elem.text if pub_date_elem is not None else '',
                        'duration': duration_elem.text if duration_elem is not None else '',
                        'guid': guid_elem.text if guid_elem is not None else '',
                    }
                    
                    if enclosure_elem is not None:
                        episode['audio_url'] = enclosure_elem.get('url', '')
                        episode['file_size'] = enclosure_elem.get('length', '0')
                        episode['mime_type'] = enclosure_elem.get('type', '')
                        # convenience for clients
                        if 'audio_url' in episode and episode['audio_url']:
                            episode['audio_filename'] = episode['audio_url'].split('/')[-1]
                    
                    # Attach transcript status
                    if episode['guid']:
                        episode['transcript_status'] = tm.get_status(episode['guid']).status
                    else:
                        episode['transcript_status'] = 'none'

                    episodes.append(episode)
            
            return jsonify({
                'episodes': episodes,
                'count': len(episodes)
            })
            
    except Exception as e:
        logger.error(f"Failed to get episodes: {e}")
        return jsonify({'error': str(e), 'episodes': []}), 500


@app.route('/api/episodes/<guid>', methods=['DELETE'])
def delete_episode(guid):
    """Delete an episode from the RSS feed."""
    try:
        logger.info(f"Delete request for episode GUID: {guid}")
        
        settings = get_settings()
        
        # Check if RSS file exists
        if not settings.rss_file.exists():
            logger.error("RSS file not found")
            return jsonify({'error': 'RSS file not found'}), 404
        
        # Parse RSS file
        import xml.etree.ElementTree as ET
        tree = ET.parse(settings.rss_file)
        root = tree.getroot()
        channel = root.find('channel')
        
        if channel is None:
            logger.error("Invalid RSS structure - no channel found")
            return jsonify({'error': 'Invalid RSS structure'}), 500
        
        # Find and remove the episode
        episode_found = False
        audio_filename = None
        
        for item in channel.findall('item'):
            guid_elem = item.find('guid')
            if guid_elem is not None and guid_elem.text == guid:
                # Extract filename from audio URL before removing
                enclosure = item.find('enclosure')
                if enclosure is not None:
                    audio_url = enclosure.get('url', '')
                    audio_filename = audio_url.split('/')[-1]
                
                # Remove the episode from feed
                channel.remove(item)
                episode_found = True
                logger.info(f"Removed episode {guid} from RSS feed")
                break
        
        if not episode_found:
            logger.warning(f"Episode {guid} not found in RSS feed")
            return jsonify({'error': 'Episode not found'}), 404
        
        # Save updated RSS file
        tree.write(settings.rss_file, encoding='utf-8', xml_declaration=True)
        logger.info(f"Saved updated RSS feed")
        
        # Optionally delete the audio file from media directory
        if audio_filename:
            audio_file = settings.media_dir / audio_filename
            if audio_file.exists():
                try:
                    audio_file.unlink()
                    logger.info(f"Deleted audio file: {audio_file}")
                except Exception as e:
                    logger.warning(f"Could not delete audio file {audio_file}: {e}")
            else:
                logger.debug(f"Audio file not found locally: {audio_file}")
        
        # Also update docs/rss.xml if auto-publish is enabled
        if settings.auto_publish == 'github':
            docs_rss = settings.base_dir / 'docs' / 'rss.xml'
            if docs_rss.exists():
                try:
                    import shutil
                    shutil.copy2(settings.rss_file, docs_rss)
                    logger.info(f"Updated docs/rss.xml")
                except Exception as e:
                    logger.warning(f"Could not update docs/rss.xml: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Episode deleted successfully',
            'guid': guid
        })
        
    except Exception as e:
        logger.error(f"Failed to delete episode {guid}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/transcripts/start', methods=['POST'])
def start_transcription():
    try:
        logger.info("=" * 60)
        logger.info("📝 Transcription start request received")
        
        payload = request.get_json(force=True)
        guid = (payload.get('guid') or '').strip()
        audio_url = (payload.get('audio_url') or '').strip()
        
        logger.info(f"GUID: {guid}")
        logger.info(f"Audio URL: {audio_url}")
        
        if not guid or not audio_url:
            logger.error("Missing guid or audio_url")
            return jsonify({'error': 'guid and audio_url are required'}), 400

        settings = get_settings()
        logger.info(f"AssemblyAI API key configured: {bool(settings.assemblyai_api_key)}")
        logger.info(f"Media dir: {settings.media_dir}")
        
        if not settings.assemblyai_api_key:
            logger.error("ASSEMBLYAI_API_KEY not set in .env!")
            return jsonify({'error': 'ASSEMBLYAI_API_KEY not configured on server'}), 500
        
        tm = get_transcript_manager()
        # ensure API key up-to-date
        tm.set_api_key(settings.assemblyai_api_key)
        
        logger.info("Calling start_transcription_background...")
        started = tm.start_transcription_background(guid, audio_url, local_media_dir=settings.media_dir)
        status = tm.get_status(guid).status
        
        logger.info(f"Started: {started}, Status: {status}")
        logger.info("=" * 60)
        
        return jsonify({'started': started, 'status': status})
    except Exception as e:
        logger.error(f"Failed to start transcription: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/transcripts/status/<guid>')
def transcript_status(guid):
    try:
        tm = get_transcript_manager()
        st = tm.get_status(guid)
        return jsonify({'guid': guid, 'status': st.status, 'error': st.error})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/transcripts/text/<guid>')
def transcript_text(guid):
    try:
        tm = get_transcript_manager()
        if not tm.has_transcript(guid):
            return jsonify({'guid': guid, 'available': False, 'text': ''}), 404
        excerpt = tm.read_transcript_excerpt(guid, max_chars=12000) or ''
        return jsonify({'guid': guid, 'available': True, 'text': excerpt})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat_with_episode():
    try:
        from config import get_settings
        settings = get_settings()
        data = request.get_json(force=True)
        message = (data.get('message') or '').strip()
        guid = (data.get('guid') or '').strip()
        history = data.get('history') or []  # optional [{role, content}]

        if not message:
            return jsonify({'error': 'message is required'}), 400
        if not settings.openai_api_key:
            return jsonify({'error': 'OPENAI_API_KEY is not configured on server'}), 500

        transcript_context = ''
        title = ''
        duration = ''
        link = ''
        audio_url = ''

        # Try to enrich with episode details from RSS
        if guid:
            try:
                # quick lookup from episodes endpoint data
                tm = get_transcript_manager()
                excerpt = tm.read_transcript_excerpt(guid, max_chars=6000)
                if excerpt:
                    transcript_context = excerpt
            except Exception:
                pass

        # Compose messages for OpenAI
        sys_prompt = (
            "Вы — дружелюбный помощник в стиле ChatGPT. Обсуждайте текущий эпизод подкаста, "
            "отвечайте кратко и по делу, ссылаясь на содержание эпизода. Если транскрипт неполный или отсутствует, "
            "отвечайте в общем ключе и уточняйте, что транскрипция ещё недоступна полностью."
        )

        messages = [{"role": "system", "content": sys_prompt}]
        if transcript_context:
            messages.append({
                "role": "system",
                "content": f"Краткий контекст эпизода (фрагмент транскрипта):\n{transcript_context}"
            })
        # add history if provided
        for h in history:
            if isinstance(h, dict) and h.get('role') in ('user', 'assistant') and isinstance(h.get('content'), str):
                messages.append({"role": h['role'], "content": h['content']})
        messages.append({"role": "user", "content": message})

        # Call OpenAI Chat Completions API via requests
        import requests
        headers = {
            'Authorization': f"Bearer {settings.openai_api_key}",
            'Content-Type': 'application/json',
        }
        payload = {
            'model': settings.openai_model,
            'messages': messages,
            'temperature': 0.3,
        }
        resp = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload, timeout=60)
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = {'message': resp.text}
            return jsonify({'error': 'LLM API error', 'details': err}), resp.status_code
        data = resp.json()
        reply = (data.get('choices') or [{}])[0].get('message', {}).get('content', '').strip()
        return jsonify({'reply': reply})
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/media/<path:filename>')
def serve_media(filename):
    """Serve media files."""
    try:
        settings = get_settings()
        return send_from_directory(settings.media_dir, filename)
    except Exception as e:
        logger.error(f"Failed to serve media file {filename}: {e}")
        return jsonify({'error': 'File not found'}), 404


@app.route('/api/proxy-audio')
def proxy_audio():
    """Proxy audio files from GitHub Releases to avoid CORS issues."""
    import requests
    from flask import Response, stream_with_context
    from urllib.parse import urlparse, unquote
    import os
    
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter required'}), 400
    
    # Only allow GitHub URLs for security
    if not url.startswith('https://github.com/'):
        return jsonify({'error': 'Only GitHub URLs allowed'}), 403
    
    def _fallback_local():
        """Serve the file from local media dir if it exists."""
        try:
            settings = get_settings()
            parsed = urlparse(url)
            filename = unquote(os.path.basename(parsed.path))
            if filename:
                local_path = settings.media_dir / filename
                if local_path.exists():
                    logger.info(f"Proxy fallback to local media for {filename}")
                    return send_from_directory(settings.media_dir, filename)
        except Exception as fe:
            logger.debug(f"Local proxy fallback failed: {fe}")
        return None

    try:
        # Stream the file from GitHub
        resp = requests.get(url, stream=True, timeout=30)
        if resp.status_code == 200:
            # Get content type from remote response
            content_type = resp.headers.get('Content-Type', 'audio/mpeg')

            def generate():
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk

            response = Response(stream_with_context(generate()), content_type=content_type)
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Cache-Control'] = 'public, max-age=31536000'

            # Copy content-length if available
            if 'Content-Length' in resp.headers:
                response.headers['Content-Length'] = resp.headers['Content-Length']

            return response

        # Non-200 from GitHub — try local fallback for 404 or other errors
        logger.warning(f"Remote audio returned {resp.status_code} for {url}")
        local_resp = _fallback_local()
        if local_resp is not None:
            return local_resp
        # If no local file, propagate meaningful status
        return jsonify({'error': 'Audio not found' if resp.status_code == 404 else 'Failed to fetch audio file'}), (
            404 if resp.status_code == 404 else 502
        )

    except requests.RequestException as e:
        # Network/error talking to GitHub — try local fallback
        local_resp = _fallback_local()
        if local_resp is not None:
            return local_resp
        logger.error(f"Failed to proxy audio from {url}: {e}")
        return jsonify({'error': 'Failed to fetch audio file'}), 502


@app.route('/rss.xml')
def serve_rss():
    """Serve RSS feed."""
    try:
        settings = get_settings()
        return send_from_directory(settings.podcast_dir, 'rss.xml', mimetype='application/rss+xml')
    except Exception as e:
        logger.error(f"Failed to serve RSS feed: {e}")
        return jsonify({'error': 'RSS feed not found'}), 404


@app.route('/api/sync-rss', methods=['POST'])
def sync_rss():
    """Sync RSS feed from GitHub Pages (docs/rss.xml) to local (podcast/rss.xml)."""
    try:
        settings = get_settings()
        
        # Path to GitHub Pages RSS
        docs_rss = settings.base_dir / 'docs' / 'rss.xml'
        podcast_rss = settings.rss_file
        
        if not docs_rss.exists():
            return jsonify({'error': 'docs/rss.xml not found'}), 404
        
        # Copy docs/rss.xml to podcast/rss.xml
        import shutil
        shutil.copy2(docs_rss, podcast_rss)
        
        logger.info(f"Synced RSS from {docs_rss} to {podcast_rss}")
        
        return jsonify({
            'success': True,
            'message': 'RSS feed synced from GitHub Pages',
            'source': str(docs_rss),
            'destination': str(podcast_rss)
        })
        
    except Exception as e:
        logger.error(f"Failed to sync RSS: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/fix-rss-namespace', methods=['POST'])
def fix_rss_namespace():
    """Fix RSS namespace issues by regenerating the feed."""
    try:
        import subprocess
        import sys
        
        settings = get_settings()
        
        # Run the fix script
        result = subprocess.run(
            [sys.executable, 'fix_rss_namespace.py'],
            capture_output=True,
            text=True,
            cwd=settings.base_dir,
            timeout=120
        )
        
        if result.returncode == 0:
            logger.info("RSS namespace fix completed successfully")
            return jsonify({
                'success': True,
                'message': 'RSS namespace fixed successfully',
                'output': result.stdout
            })
        else:
            logger.error(f"RSS namespace fix failed: {result.stderr}")
            return jsonify({
                'success': False,
                'message': 'RSS namespace fix failed',
                'error': result.stderr
            }), 500
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Script execution timed out'}), 500
    except Exception as e:
        logger.error(f"RSS namespace fix error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Check configuration
    try:
        settings = get_settings()
        settings.ensure_directories()
        logger.info("Configuration loaded successfully")
        logger.info(f"Starting web server for: {settings.podcast_title}")
        
        # Get port from environment (Railway, Render, etc.) or default to 5001
        port = int(os.environ.get('PORT', 5001))
        logger.info(f"Starting server on port {port}")
        
        # Debug mode only for local development
        debug = os.environ.get('ENVIRONMENT', 'development') == 'development'
        
        app.run(debug=debug, host='0.0.0.0', port=port)
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please configure .env file before starting")
        exit(1)
