"""
Logging configuration for YouTube to Podcast converter.
"""

import logging
import sys
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler


def get_log_level_from_env() -> int:
    """
    Get logging level from environment variable LOG_LEVEL.
    
    Returns:
        Logging level (default: INFO)
    """
    level_name = os.environ.get('LOG_LEVEL', 'INFO').upper()
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }
    return level_map.get(level_name, logging.INFO)


def setup_logger(name: str = "yt2pod", level: int = None, log_file: str = None) -> logging.Logger:
    """
    Configure and return a logger with console and optional file output.
    
    Args:
        name: Logger name
        level: Logging level (default: from LOG_LEVEL env var or INFO)
        log_file: Optional log file path (default: logs/{name}.log)
    
    Returns:
        Configured logger instance
    """
    # Use provided level, or get from environment, or default to INFO
    if level is None:
        level = get_log_level_from_env()
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding multiple handlers if logger already exists
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file is None:
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"{name}.log"
    else:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Rotating file handler: max 10MB, keep 5 backup files
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "yt2pod") -> logging.Logger:
    """
    Get an existing logger or create a new one.
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
