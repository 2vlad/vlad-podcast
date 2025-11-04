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
from utils.rss_manager import RSSManager, EpisodeData
from utils.github_publisher import GitHubPublisher

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


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_upload_job(job_id: int, file_path: Path, original_filename: str, title: str = None, description: str = None):
    """Background job to process an uploaded audio/video file."""
    global jobs
    
    try:
        jobs[job_id]['status'] = 'processing'
        jobs[job_id]['message'] = 'Processing uploaded file...'
        jobs[job_id]['progress'] = {'status': 'processing', 'percent': 0}
        
        settings = get_settings()
        
        # Generate unique ID from file content
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()[:11]
        
        jobs[job_id]['video_id'] = file_hash
        
        # Determine file extension
        ext = file_path.suffix.lower()
        target_format = settings.audio_format
        
        # Convert to target format if needed
        if ext == '.mp4':
            jobs[job_id]['message'] = 'Converting MP4 to audio...'
            jobs[job_id]['progress'] = {'status': 'converting', 'percent': 50}
            
            # Use ffmpeg to convert
            output_file = settings.media_dir / f"{file_hash}.{target_format}"
            import subprocess
            
            cmd = [
                'ffmpeg', '-i', str(file_path),
                '-vn',  # No video
                '-acodec', 'aac' if target_format == 'm4a' else 'libmp3lame',
                '-q:a', '2',  # Quality
                str(output_file)
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                file_path.unlink()  # Remove original file
                audio_file = output_file
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg conversion failed: {e.stderr.decode()}")
                # If conversion fails, just rename the file
                audio_file = file_path.rename(settings.media_dir / f"{file_hash}{ext}")
        else:
            # MP3/M4A files - just rename
            audio_file = file_path.rename(settings.media_dir / f"{file_hash}{ext}")
        
        jobs[job_id]['message'] = 'Extracting metadata...'
        jobs[job_id]['progress'] = {'status': 'metadata', 'percent': 75}
        
        # Get file size
        file_size = audio_file.stat().st_size
        
        # Use provided title or filename
        if not title:
            title = Path(original_filename).stem
        
        if not description:
            description = f"Uploaded audio: {original_filename}"
        
        jobs[job_id]['title'] = title
        jobs[job_id]['duration'] = 'Unknown'  # Could extract with ffprobe if needed
        
        jobs[job_id]['message'] = 'Updating RSS feed...'
        jobs[job_id]['progress'] = {'status': 'feed', 'percent': 90}
        
        # Update RSS
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
            fg = rss_manager.create_feed()
        
        existing_guids = rss_manager.get_existing_guids(settings.rss_file)
        
        if file_hash in existing_guids:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['message'] = 'Already in feed'
            jobs[job_id]['duplicate'] = True
            return
        
        # Add episode
        audio_url = f"{settings.media_base_url}/{audio_file.name}"
        mime_type = "audio/mp4" if audio_file.suffix == '.m4a' else "audio/mpeg"
        
        episode = EpisodeData(
            guid=file_hash,
            title=title,
            link=settings.site_url,  # No external link for uploads
            description=description,
            audio_url=audio_url,
            audio_file_size=file_size,
            audio_mime_type=mime_type,
            pub_date=datetime.now(timezone.utc),
            duration=None,  # Unknown for uploaded files
            image_url=None,  # No thumbnail for uploads
        )
        
        rss_manager.add_episode(fg, episode)
        rss_manager.save_feed(fg, settings.rss_file, max_items=settings.feed_max_items)
        
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['message'] = 'Upload completed successfully!'
        jobs[job_id]['progress'] = {'status': 'completed', 'percent': 100}
        
        logger.info(f"Successfully processed uploaded file: {original_filename} (ID: {file_hash})")
        
    except Exception as e:
        logger.error(f"Failed to process upload: {e}", exc_info=True)
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
        
        jobs[job_id]['message'] = 'Updating RSS feed...'
        jobs[job_id]['title'] = metadata.title
        jobs[job_id]['duration'] = metadata.formatted_duration
        
        # Update RSS
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
            fg = rss_manager.create_feed()
        
        existing_guids = rss_manager.get_existing_guids(settings.rss_file)
        
        if metadata.video_id in existing_guids:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['message'] = 'Already in feed'
            jobs[job_id]['duplicate'] = True
            return
        
        # Add episode
        audio_url = f"{settings.media_base_url}/{audio_file.name}"
        file_size = audio_file.stat().st_size
        mime_type = "audio/mp4" if settings.audio_format == "m4a" else "audio/mpeg"
        
        episode = EpisodeData(
            guid=metadata.video_id,
            title=metadata.title,
            link=metadata.webpage_url or parsed_url.normalized_url,
            description=metadata.description or metadata.title,
            audio_url=audio_url,
            audio_file_size=file_size,
            audio_mime_type=mime_type,
            pub_date=metadata.pub_date,
            duration=metadata.formatted_duration,
            image_url=metadata.thumbnail_url,
        )
        
        rss_manager.add_episode(fg, episode)
        rss_manager.save_feed(fg, settings.rss_file, max_items=settings.feed_max_items)
        
        # Auto-publish to GitHub Pages if configured
        if settings.auto_publish == 'github':
            jobs[job_id]['message'] = 'Publishing to GitHub Pages...'
            jobs[job_id]['progress'] = {'status': 'publishing', 'percent': 100}
            
            try:
                publisher = GitHubPublisher(
                    repo_path=settings.base_dir,
                    branch=settings.github_branch
                )
                
                # Publish (sync RSS to docs, git add, commit, push)
                publish_success = publisher.publish(
                    episode_title=metadata.title,
                    rss_file=settings.rss_file,
                    patterns=["docs/"]
                )
                
                if publish_success:
                    pages_url = f"https://2vlad.github.io/vlad-podcast/rss.xml"
                    jobs[job_id]['message'] = f'Published to GitHub Pages!'
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
    
    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    # Get optional metadata
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    
    try:
        settings = get_settings()
        
        # Create temp directory if it doesn't exist
        temp_dir = settings.podcast_dir / 'temp'
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = temp_dir / filename
        file.save(str(temp_path))
        
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
        
        # Start background processing
        thread = threading.Thread(
            target=process_upload_job,
            args=(job_id, temp_path, filename, title or None, description or None)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'status': 'pending',
            'filename': filename
        })
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
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
                    
                    episodes.append(episode)
            
            return jsonify({
                'episodes': episodes,
                'count': len(episodes)
            })
            
    except Exception as e:
        logger.error(f"Failed to get episodes: {e}")
        return jsonify({'error': str(e), 'episodes': []}), 500


@app.route('/media/<path:filename>')
def serve_media(filename):
    """Serve media files."""
    try:
        settings = get_settings()
        return send_from_directory(settings.media_dir, filename)
    except Exception as e:
        logger.error(f"Failed to serve media file {filename}: {e}")
        return jsonify({'error': 'File not found'}), 404


@app.route('/rss.xml')
def serve_rss():
    """Serve RSS feed."""
    try:
        settings = get_settings()
        return send_from_directory(settings.podcast_dir, 'rss.xml', mimetype='application/rss+xml')
    except Exception as e:
        logger.error(f"Failed to serve RSS feed: {e}")
        return jsonify({'error': 'RSS feed not found'}), 404


if __name__ == '__main__':
    # Check configuration
    try:
        settings = get_settings()
        settings.ensure_directories()
        logger.info("Configuration loaded successfully")
        logger.info(f"Starting web server for: {settings.podcast_title}")
        logger.info("Open http://localhost:5000 in your browser")
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please configure .env file before starting")
        exit(1)
    
    app.run(debug=True, host='0.0.0.0', port=5001)
