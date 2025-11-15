"""
Audio splitter utility for splitting long audio files into multiple episodes.
Uses ffmpeg to split audio files without re-encoding (fast and lossless).
"""

import subprocess
import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AudioSegment:
    """Information about an audio segment."""
    file_path: Path
    part_number: int
    total_parts: int
    start_time: int  # seconds
    duration: int    # seconds
    
    @property
    def title_suffix(self) -> str:
        """Get the title suffix for this segment."""
        return f" (Part {self.part_number}/{self.total_parts})"
    
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


class AudioSplitter:
    """Split audio files into multiple segments."""
    
    # Maximum duration for a single episode in seconds (1 hour)
    MAX_EPISODE_DURATION = 3600
    
    def __init__(self, max_duration: int = MAX_EPISODE_DURATION):
        """
        Initialize audio splitter.
        
        Args:
            max_duration: Maximum duration per segment in seconds (default: 3600 = 1 hour)
        """
        self.max_duration = max_duration
    
    def should_split(self, duration: int) -> bool:
        """
        Check if audio file should be split based on duration.
        
        Args:
            duration: Duration in seconds
            
        Returns:
            True if duration exceeds max_duration
        """
        return duration > self.max_duration
    
    def calculate_segments(self, total_duration: int) -> List[tuple[int, int]]:
        """
        Calculate segment boundaries for splitting.
        
        Args:
            total_duration: Total duration in seconds
            
        Returns:
            List of (start_time, duration) tuples for each segment
        """
        if total_duration <= self.max_duration:
            return [(0, total_duration)]
        
        segments = []
        remaining = total_duration
        start_time = 0
        
        while remaining > 0:
            segment_duration = min(self.max_duration, remaining)
            segments.append((start_time, segment_duration))
            start_time += segment_duration
            remaining -= segment_duration
        
        return segments
    
    def get_audio_duration(self, audio_file: Path) -> int:
        """
        Get duration of audio file using ffprobe.
        
        Args:
            audio_file: Path to audio file
            
        Returns:
            Duration in seconds
            
        Raises:
            Exception: If ffprobe fails
        """
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(audio_file)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return int(float(result.stdout.strip()))
        except subprocess.CalledProcessError as e:
            logger.error(f"ffprobe failed: {e.stderr}")
            raise Exception(f"Failed to get audio duration: {e.stderr}")
    
    def split_audio(
        self,
        audio_file: Path,
        output_dir: Optional[Path] = None,
        base_name: Optional[str] = None
    ) -> List[AudioSegment]:
        """
        Split audio file into multiple segments.
        
        Uses ffmpeg copy mode for fast, lossless splitting.
        
        Args:
            audio_file: Path to audio file to split
            output_dir: Directory for output files (default: same as input)
            base_name: Base name for output files (default: input filename without extension)
            
        Returns:
            List of AudioSegment objects
            
        Raises:
            Exception: If splitting fails
        """
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file}")
        
        # Get audio duration
        total_duration = self.get_audio_duration(audio_file)
        
        # Check if splitting is needed
        if not self.should_split(total_duration):
            logger.info(f"Audio duration ({total_duration}s) is within limit, no splitting needed")
            return []
        
        # Calculate segments
        segments_info = self.calculate_segments(total_duration)
        num_parts = len(segments_info)
        
        logger.info(f"Splitting audio ({total_duration}s) into {num_parts} parts of max {self.max_duration}s each")
        
        # Setup output
        if output_dir is None:
            output_dir = audio_file.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if base_name is None:
            base_name = audio_file.stem
        
        extension = audio_file.suffix
        
        # Split into segments
        segments = []
        
        for i, (start_time, duration) in enumerate(segments_info, 1):
            part_file = output_dir / f"{base_name}_part{i}{extension}"
            
            # Use ffmpeg to extract segment
            # -ss: start time, -t: duration, -c copy: no re-encoding (fast)
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file
                '-loglevel', 'error',  # Only show errors
                '-i', str(audio_file),
                '-ss', str(start_time),
                '-t', str(duration),
                '-c', 'copy',  # Copy codec (no re-encoding)
                '-map_metadata', '0',  # Copy metadata
                str(part_file)
            ]
            
            try:
                logger.info(f"Creating part {i}/{num_parts}: {part_file.name} ({duration}s)")
                subprocess.run(cmd, check=True, capture_output=True)
                
                segment = AudioSegment(
                    file_path=part_file,
                    part_number=i,
                    total_parts=num_parts,
                    start_time=start_time,
                    duration=duration
                )
                segments.append(segment)
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to create segment {i}: {e.stderr.decode()}")
                # Clean up partial files
                for seg in segments:
                    if seg.file_path.exists():
                        seg.file_path.unlink()
                raise Exception(f"Failed to split audio: {e.stderr.decode()}")
        
        logger.info(f"Successfully split audio into {len(segments)} parts")
        return segments
    
    def cleanup_segments(self, segments: List[AudioSegment]):
        """
        Remove segment files from disk.
        
        Args:
            segments: List of AudioSegment objects to clean up
        """
        for segment in segments:
            if segment.file_path.exists():
                try:
                    segment.file_path.unlink()
                    logger.debug(f"Removed segment: {segment.file_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove segment {segment.file_path}: {e}")
