"""
Audio converter utility using FFmpeg.
Converts audio files to MP3 format with high quality settings.
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class AudioConverterError(Exception):
    """Raised when audio conversion fails."""
    pass


def is_mp3(file_path: Path) -> bool:
    """
    Check if file is already in MP3 format.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        True if file is MP3, False otherwise
    """
    return file_path.suffix.lower() == '.mp3'


def get_audio_info(file_path: Path) -> dict:
    """
    Get audio file information using FFprobe.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Dictionary with audio info (codec, bitrate, duration, etc.)
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-loglevel', 'error',  # Suppress warnings
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(file_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        import json
        return json.loads(result.stdout)
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get audio info: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error getting audio info: {e}")
        return {}


def convert_to_mp3(
    input_path: Path,
    output_path: Optional[Path] = None,
    quality: int = 2,
    bitrate: Optional[str] = None,
    keep_original: bool = False
) -> Path:
    """
    Convert audio file to MP3 format using FFmpeg.
    
    Args:
        input_path: Path to input audio file
        output_path: Path for output MP3 file (default: same name with .mp3)
        quality: VBR quality (0-9, where 0 is best, 2 is ~190kbps - recommended)
        bitrate: CBR bitrate (e.g., '192k', '256k') - overrides quality if set
        keep_original: If True, keeps the original file after conversion
        
    Returns:
        Path to the converted MP3 file
        
    Raises:
        AudioConverterError: If conversion fails
    """
    if not input_path.exists():
        raise AudioConverterError(f"Input file not found: {input_path}")
    
    # If already MP3, just return the path
    if is_mp3(input_path):
        logger.info(f"File is already MP3: {input_path}")
        return input_path
    
    # Generate output path if not provided
    if output_path is None:
        output_path = input_path.with_suffix('.mp3')
    
    logger.info(f"Converting {input_path.name} to MP3...")
    
    # Build FFmpeg command
    cmd = [
        'ffmpeg',
        '-loglevel', 'error',  # Only show errors, suppress warnings
        '-i', str(input_path),
        '-vn',  # No video
        '-acodec', 'libmp3lame',
    ]
    
    # Add quality/bitrate settings
    if bitrate:
        # Constant bitrate mode
        cmd.extend(['-b:a', bitrate])
        logger.info(f"Using CBR: {bitrate}")
    else:
        # Variable bitrate mode (better quality/size ratio)
        cmd.extend(['-q:a', str(quality)])
        logger.info(f"Using VBR quality: {quality} (~{_quality_to_bitrate(quality)})")
    
    # Additional settings for compatibility
    cmd.extend([
        '-ar', '44100',  # Sample rate: 44.1kHz (standard)
        '-ac', '2',      # Channels: stereo
        '-y',            # Overwrite output file
        str(output_path)
    ])
    
    try:
        # Run conversion
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info(f"✅ Conversion successful: {output_path.name}")
        
        # Remove original file if requested
        if not keep_original and output_path != input_path:
            logger.info(f"Removing original file: {input_path.name}")
            input_path.unlink()
        
        return output_path
        
    except subprocess.CalledProcessError as e:
        error_msg = f"FFmpeg conversion failed: {e.stderr}"
        logger.error(error_msg)
        raise AudioConverterError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error during conversion: {e}"
        logger.error(error_msg)
        raise AudioConverterError(error_msg)


def batch_convert_to_mp3(
    input_dir: Path,
    output_dir: Optional[Path] = None,
    quality: int = 2,
    extensions: Tuple[str, ...] = ('.m4a', '.mp4', '.aac', '.ogg', '.flac', '.wav')
) -> list[Path]:
    """
    Convert all audio files in a directory to MP3.
    
    Args:
        input_dir: Directory containing audio files
        output_dir: Directory for output files (default: same as input)
        quality: VBR quality (0-9)
        extensions: Tuple of file extensions to convert
        
    Returns:
        List of paths to converted MP3 files
    """
    if not input_dir.exists():
        raise AudioConverterError(f"Input directory not found: {input_dir}")
    
    if output_dir is None:
        output_dir = input_dir
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    converted = []
    
    for ext in extensions:
        for input_file in input_dir.glob(f'*{ext}'):
            try:
                output_file = output_dir / input_file.with_suffix('.mp3').name
                result = convert_to_mp3(input_file, output_file, quality=quality)
                converted.append(result)
            except AudioConverterError as e:
                logger.error(f"Failed to convert {input_file.name}: {e}")
    
    return converted


def _quality_to_bitrate(quality: int) -> str:
    """Map VBR quality level to approximate bitrate."""
    quality_map = {
        0: '245kbps',
        1: '225kbps',
        2: '190kbps',
        3: '175kbps',
        4: '165kbps',
        5: '130kbps',
        6: '115kbps',
        7: '100kbps',
        8: '85kbps',
        9: '65kbps',
    }
    return quality_map.get(quality, '~190kbps')


# Command-line interface
if __name__ == '__main__':
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 2:
        print("Usage: python audio_converter.py <input_file> [output_file] [quality]")
        print("Quality: 0-9 (0=best, 2=recommended ~190kbps, 9=worst)")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    quality = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    
    try:
        result = convert_to_mp3(input_path, output_path, quality)
        print(f"✅ Successfully converted to: {result}")
    except AudioConverterError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
