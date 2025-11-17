"""
Centralized logging configuration with UTF-8 support for Windows
Ensures emojis and Unicode characters display correctly
"""

import logging
import sys
import io
from pathlib import Path


def setup_logging(name: str = None, log_file: str = './data/tradego.log', level=logging.INFO):
    """
    Configure logging with UTF-8 encoding for Windows compatibility

    Args:
        name: Logger name (use __name__ from calling module)
        log_file: Path to log file
        level: Logging level

    Returns:
        Configured logger instance
    """
    # Ensure data directory exists
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Create UTF-8 stream handler for console output (Windows compatible)
    console_handler = logging.StreamHandler(sys.stdout)
    try:
        # Try to set UTF-8 encoding on stdout
        console_handler.stream = io.TextIOWrapper(
            sys.stdout.buffer,
            encoding='utf-8',
            line_buffering=True
        )
    except (AttributeError, io.UnsupportedOperation):
        # If stdout doesn't have buffer (e.g., in some IDEs), fall back to default
        pass

    # Create file handler with UTF-8 encoding
    file_handler = logging.FileHandler(log_file, encoding='utf-8')

    # Set format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Get or create logger
    logger = logging.getLogger(name) if name else logging.getLogger()
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = None):
    """
    Get a logger instance (assumes setup_logging was called at app start)

    Args:
        name: Logger name (use __name__ from calling module)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
