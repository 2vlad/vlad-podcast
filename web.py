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
from datetime import datetime

from config import get_settings, ConfigurationError
from utils.logger import setup_logger
from utils.url_processor import process_urls
from utils.downloader import AudioDownloader
from utils.rss_manager import RSSManager, EpisodeData
from utils.github_publisher import GitHubPublisher

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

logger = setup_logger("web")

# Job status tracking
jobs = {}
job_id_counter = 0
job_lock = threading.Lock()


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
                
                # Publish (git add, commit, push)
                publish_success = publisher.publish(
                    episode_title=metadata.title,
                    patterns=["podcast/"]
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
