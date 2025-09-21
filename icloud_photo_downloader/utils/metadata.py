"""Handle photo metadata and EXIF information."""

import os
import time
import logging
from typing import Any, Dict, Optional
from datetime import datetime
import piexif
from PIL import Image

logger = logging.getLogger(__name__)

class MetadataHandler:
    """Handle photo metadata and EXIF information."""
    
    @staticmethod
    def preserve_timestamps(filepath: str, created_date: Optional[datetime]) -> None:
        """Preserve the original creation and modification dates of the file.
        
        Args:
            filepath: Path to the file
            created_date: Original creation date
        """
        try:
            if created_date:
                timestamp = time.mktime(created_date.timetuple())
                os.utime(filepath, (timestamp, timestamp))
                logger.debug(f"Preserved timestamps for {filepath}")
        except Exception as e:
            logger.warning(f"Could not preserve timestamps for {filepath}: {str(e)}")
    
    @staticmethod
    def save_exif_data(photo: Any, filepath: str) -> None:
        """Save photo EXIF metadata.
        
        Args:
            photo: iCloud photo object
            filepath: Path to the saved file
        """
        try:
            if not filepath.lower().endswith(('.jpg', '.jpeg')):
                logger.debug(f"Skipping EXIF for non-JPEG file: {filepath}")
                return
            
            # Initialize EXIF dictionary
            exif_dict: Dict = {
                "0th": {},
                "Exif": {},
                "GPS": {},
                "1st": {},
                "thumbnail": None
            }
            
            # Try to read existing EXIF data
            try:
                if os.path.exists(filepath):
                    img = Image.open(filepath)
                    if 'exif' in img.info:
                        exif_dict = piexif.load(img.info['exif'])
            except Exception as e:
                logger.warning(f"Could not read existing EXIF data: {str(e)}")
            
            # Update creation date
            if hasattr(photo, 'created'):
                date_time = photo.created
                date_str = date_time.strftime("%Y:%m:%d %H:%M:%S")
                
                exif_dict["0th"][piexif.ImageIFD.DateTime] = date_str
                exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_str
                exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_str
            
            # Update GPS data
            if hasattr(photo, 'location') and photo.location:
                location = photo.location
                if 'latitude' in location and 'longitude' in location:
                    lat = location['latitude']
                    lon = location['longitude']
                    
                    exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = \
                        MetadataHandler._convert_to_degrees(abs(lat))
                    exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = \
                        MetadataHandler._convert_to_degrees(abs(lon))
                    exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = 'N' if lat >= 0 else 'S'
                    exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = 'E' if lon >= 0 else 'W'
            
            # Save EXIF data
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, filepath)
            logger.debug(f"Saved EXIF data for {filepath}")
            
        except Exception as e:
            logger.warning(f"Could not save EXIF data for {filepath}: {str(e)}")
    
    @staticmethod
    def _convert_to_degrees(value: float) -> tuple:
        """Convert decimal GPS coordinates to degrees format.
        
        Args:
            value: Decimal coordinate value
            
        Returns:
            tuple: Degrees, minutes, seconds
        """
        degrees = int(value)
        minutes = int((value - degrees) * 60)
        seconds = int(((value - degrees) * 60 - minutes) * 60 * 100)
        return ((degrees, 1), (minutes, 1), (seconds, 100))