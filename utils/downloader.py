"""
YouTube audio download and metadata extraction using yt-dlp.
"""

import yt_dlp
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class VideoMetadata:
    """Video metadata extracted from YouTube."""
    video_id: str
    title: str
    description: str
    duration: int  # seconds
    upload_date: str  # YYYYMMDD format
    uploader: str
    thumbnail_url: Optional[str] = None
    webpage_url: Optional[str] = None
    
    @property
    def formatted_duration(self) -> str:
        """Return duration in HH:MM:SS format."""
        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    @property
    def pub_date(self) -> datetime:
        """Convert upload_date to datetime object with UTC timezone."""
        from datetime import timezone
        dt = datetime.strptime(self.upload_date, "%Y%m%d")
        return dt.replace(tzinfo=timezone.utc)


class AudioDownloader:
    """Download audio from YouTube videos using yt-dlp."""
    
    def __init__(self, output_dir: Path, audio_format: str = "m4a", progress_callback=None):
        """
        Initialize downloader.
        
        Args:
            output_dir: Directory to save audio files
            audio_format: Audio format (m4a or mp3)
            progress_callback: Optional callback function for progress updates
                               Called with dict: {'status': str, 'percent': float, 'speed': str, 'eta': str}
        """
        self.output_dir = Path(output_dir)
        self.audio_format = audio_format
        self.progress_callback = progress_callback
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _progress_hook(self, d):
        """Hook for yt-dlp progress updates."""
        if self.progress_callback:
            if d['status'] == 'downloading':
                # Parse percentage
                percent_str = d.get('_percent_str', '0%').strip()
                percent = float(percent_str.replace('%', ''))
                
                # Get speed and ETA
                speed = d.get('_speed_str', 'N/A').strip()
                eta = d.get('_eta_str', 'N/A').strip()
                
                self.progress_callback({
                    'status': 'downloading',
                    'percent': percent,
                    'speed': speed,
                    'eta': eta,
                    'downloaded': d.get('downloaded_bytes', 0),
                    'total': d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0),
                })
            elif d['status'] == 'finished':
                self.progress_callback({
                    'status': 'converting',
                    'percent': 100,
                    'speed': 'N/A',
                    'eta': '0s',
                })
    
    def get_yt_dlp_options(self, video_id: str) -> Dict:
        """
        Get yt-dlp options for audio download.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary of yt-dlp options
        """
        output_template = str(self.output_dir / f"{video_id}.%(ext)s")
        
        options = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'writethumbnail': False,
            'progress_hooks': [self._progress_hook] if self.progress_callback else [],
            # Fix for 403 errors - updated for 2025
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'extractor_args': {'youtube': {'player_client': ['ios', 'android', 'web']}},
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            },
        }
        
        # Add postprocessors for format conversion
        if self.audio_format == 'm4a':
            options['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '0',  # Best quality
            }]
        elif self.audio_format == 'mp3':
            options['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',  # 320 kbps
            }]
        
        return options
    
    def extract_metadata(self, url: str) -> VideoMetadata:
        """
        Extract metadata from YouTube video without downloading.
        
        Args:
            url: YouTube video URL
            
        Returns:
            VideoMetadata object
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            # Fix for 403 errors
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'extractor_args': {'youtube': {'player_client': ['ios', 'android', 'web']}},
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            return VideoMetadata(
                video_id=info['id'],
                title=info.get('title', 'Unknown Title'),
                description=info.get('description', ''),
                duration=info.get('duration', 0),
                upload_date=info.get('upload_date', datetime.now().strftime("%Y%m%d")),
                uploader=info.get('uploader', 'Unknown'),
                thumbnail_url=info.get('thumbnail'),
                webpage_url=info.get('webpage_url'),
            )
    
    def download_audio(self, url: str, video_id: str) -> Path:
        """
        Download audio from YouTube video.
        
        Args:
            url: YouTube video URL
            video_id: YouTube video ID
            
        Returns:
            Path to downloaded audio file
            
        Raises:
            Exception: If download fails
        """
        options = self.get_yt_dlp_options(video_id)
        
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
        
        # Find the downloaded file
        audio_file = self.output_dir / f"{video_id}.{self.audio_format}"
        
        if not audio_file.exists():
            raise FileNotFoundError(
                f"Audio file not found after download: {audio_file}"
            )
        
        return audio_file
    
    def download_with_metadata(self, url: str, video_id: str) -> tuple[Path, VideoMetadata]:
        """
        Download audio and extract metadata.
        
        Args:
            url: YouTube video URL
            video_id: YouTube video ID
            
        Returns:
            Tuple of (audio_file_path, metadata)
        """
        # Extract metadata first
        metadata = self.extract_metadata(url)
        
        # Download audio
        audio_file = self.download_audio(url, video_id)
        
        return audio_file, metadata
