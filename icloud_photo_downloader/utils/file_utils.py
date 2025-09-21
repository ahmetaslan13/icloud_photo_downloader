"""Utility functions for iCloud Photo Downloader."""

import os
import sys
import shutil
import logging
from typing import Tuple, Optional
from datetime import datetime
import calendar

logger = logging.getLogger(__name__)

def check_disk_space(directory: str, required_space_gb: float = 10.0) -> Optional[float]:
    """Check if there's enough space on the target drive.
    
    Args:
        directory: Path to check for space
        required_space_gb: Required free space in GB
        
    Returns:
        float: Available space in GB if sufficient, None if error
    """
    try:
        total, used, free = shutil.disk_usage(directory)
        free_gb = free / (1024 * 1024 * 1024)  # Convert to GB
        
        if free_gb < required_space_gb:
            logger.warning(
                f"Low disk space: Only {free_gb:.1f}GB free, "
                f"{required_space_gb}GB required"
            )
            return free_gb
        
        logger.debug(f"Sufficient disk space: {free_gb:.1f}GB available")
        return free_gb
        
    except Exception as e:
        logger.error(f"Error checking disk space: {str(e)}")
        return None

def create_directory_structure(base_dir: str, file_type: str, 
                             year: int, month: int) -> str:
    """Create nested directories for organizing photos.
    
    Args:
        base_dir: Base directory path
        file_type: Type of media (HEIC, JPEG, etc.)
        year: Year for organization
        month: Month for organization
        
    Returns:
        str: Path to created directory
    """
    try:
        # Create type directory
        type_dir = os.path.join(base_dir, file_type)
        os.makedirs(type_dir, exist_ok=True)
        
        # Create year directory
        year_dir = os.path.join(type_dir, str(year))
        os.makedirs(year_dir, exist_ok=True)
        
        # Create month directory with number and name (e.g., "01-January")
        month_name = calendar.month_name[month]
        month_dir = os.path.join(year_dir, f"{month:02d}-{month_name}")
        os.makedirs(month_dir, exist_ok=True)
        
        logger.debug(f"Created directory structure: {month_dir}")
        return month_dir
        
    except Exception as e:
        logger.error(f"Error creating directory structure: {str(e)}")
        raise

def get_date_from_filename(filename: str) -> Tuple[int, int]:
    """Extract year and month from a filename if it contains a date.
    
    Args:
        filename: Name of the file
        
    Returns:
        Tuple[int, int]: Year and month, or current year/month if not found
    """
    try:
        # Try to extract YYYYMMDD from filename
        parts = filename.split('_')
        for part in parts:
            if len(part) == 8 and part.isdigit():
                year = int(part[:4])
                month = int(part[4:6])
                if 1 <= month <= 12:
                    return year, month
    except Exception:
        pass
    
    # If no valid date found, use current date
    now = datetime.now()
    return now.year, now.month

def get_file_type(filename: str) -> str:
    """Determine the appropriate folder based on file extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        str: File type category
    """
    ext = os.path.splitext(filename)[1].lower()
    
    type_mapping = {
        '.heic': 'HEIC',
        '.jpg': 'JPEG',
        '.jpeg': 'JPEG',
        '.png': 'PNG',
        '.mov': 'Videos',
        '.mp4': 'Videos',
        '.m4v': 'Videos',
        '.gif': 'GIF',
        '.raw': 'RAW',
        '.dng': 'RAW',
        '.cr2': 'RAW',
        '.arw': 'RAW'
    }
    
    return type_mapping.get(ext, 'Others')

def safe_filename(filename: str) -> str:
    """Create a safe filename that works across platforms.
    
    Args:
        filename: Original filename
        
    Returns:
        str: Safe filename
    """
    # Replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # Ensure filename isn't too long (max 255 chars)
    name, ext = os.path.splitext(filename)
    if len(filename) > 255:
        return name[:255-len(ext)] + ext
    
    return filename