"""Core photo downloader functionality."""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from tqdm import tqdm
import hashlib
import tempfile

from .auth import ICloudAuth
from .config import Config
from ..utils.file_utils import (
    check_disk_space,
    create_directory_structure,
    get_file_type,
    safe_filename
)
from ..utils.metadata import MetadataHandler

logger = logging.getLogger(__name__)

class PhotoDownloader:
    """Main photo downloader class."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize PhotoDownloader.
        
        Args:
            config_path: Optional path to custom config file
        """
        self.config = Config(config_path)
        self.auth = ICloudAuth()
        self.metadata = MetadataHandler()
        self.api = None
        self.stats: Dict[str, Any] = {}
        
    def start(self, apple_id: str, password: str) -> None:
        """Start the download process.
        
        Args:
            apple_id: Apple ID for authentication
            password: iCloud password
        """
        try:
            # Authenticate
            self.api = self.auth.authenticate(apple_id, password)
            
            # Get base directory
            base_dir = self._setup_output_directory()
            
            # Check disk space
            required_space = self.config.get('download.required_space_gb', 10)
            if not check_disk_space(base_dir, required_space):
                if not self._confirm_continue():
                    logger.info("Download cancelled by user")
                    return
            
            # Start downloading
            self._download_all_photos(base_dir)
            
        except Exception as e:
            logger.error(f"Error during download process: {str(e)}")
            raise
        
    def _setup_output_directory(self) -> str:
        """Set up the output directory structure.
        
        Returns:
            str: Path to output directory
        """
        base_dir = self.config.download_path
        
        if self.config.get('download.create_timestamp_folder'):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_dir = os.path.join(base_dir, f"download_{timestamp}")
        
        os.makedirs(base_dir, exist_ok=True)
        logger.info(f"Using output directory: {base_dir}")
        return base_dir
    
    def _confirm_continue(self) -> bool:
        """Ask user to confirm continuation.
        
        Returns:
            bool: True if user wants to continue
        """
        response = input("Do you want to continue anyway? (y/n): ")
        return response.lower() == 'y'
    
    def _download_all_photos(self, base_dir: str) -> None:
        """Download all photos from iCloud.
        
        Args:
            base_dir: Base directory for downloads
        """
        # Download personal library
        if self.api.photos.all:
            self._download_photo_library(base_dir, "Personal")
        
        # Download shared photos
        if self.config.get('options.download_shared') and self.api.photos.shared:
            self._download_photo_library(base_dir, "Shared_With_Me")
        
        # Download shared albums
        if self.config.get('options.download_albums'):
            self._download_shared_albums(base_dir)
    
    def _download_photo_library(self, base_dir: str, library_type: str) -> None:
        """Download photos from a specific library.
        
        Args:
            base_dir: Base directory for downloads
            library_type: Type of library (Personal/Shared_With_Me)
        """
        photos = self.api.photos.all if library_type == "Personal" else self.api.photos.shared.all
        total = len(photos)
        
        logger.info(f"Downloading {library_type} library ({total} photos)")
        
        for photo in tqdm(photos, desc=f"{library_type} Photos", unit="photo"):
            try:
                success = self._process_single_photo(photo, base_dir, library_type)
                if success:
                    self._update_stats(library_type, photo)
            except Exception as e:
                logger.error(f"Error processing photo {photo.filename}: {str(e)}")
    
    def _download_shared_albums(self, base_dir: str) -> None:
        """Download photos from shared albums.
        
        Args:
            base_dir: Base directory for downloads
        """
        albums = self.api.photos.shared.albums
        if not albums:
            logger.info("No shared albums found")
            return
        
        logger.info(f"Found {len(albums)} shared albums")
        
        for album in albums:
            try:
                album_name = album.name
                photos = album.photos
                logger.info(f"Processing album '{album_name}' ({len(photos)} photos)")
                
                for photo in tqdm(photos, desc=f"Album: {album_name}", unit="photo"):
                    try:
                        success = self._process_single_photo(
                            photo, base_dir, "Shared_Albums", album_name
                        )
                        if success:
                            self._update_stats("Shared_Albums", photo, album_name)
                    except Exception as e:
                        logger.error(
                            f"Error processing photo {photo.filename} "
                            f"from album {album_name}: {str(e)}"
                        )
            except Exception as e:
                logger.error(f"Error processing album {album.name}: {str(e)}")
    
    def _process_single_photo(self, photo: Any, base_dir: str,
                            photo_type: str, album_name: Optional[str] = None) -> bool:
        """Process and download a single photo.
        
        Args:
            photo: Photo object to process
            base_dir: Base directory for downloads
            photo_type: Type of photo (Personal/Shared_With_Me/Shared_Albums)
            album_name: Optional album name for shared albums
            
        Returns:
            bool: True if successful
        """
        try:
            # Get photo details
            filename = safe_filename(photo.filename)
            created_date = getattr(photo, 'created', None)
            
            # Determine directory structure
            if album_name:
                photo_dir = os.path.join(base_dir, "Shared_Albums", album_name)
                os.makedirs(photo_dir, exist_ok=True)
            else:
                year, month = self._get_photo_date(photo)
                file_type = get_file_type(filename)
                photo_dir = create_directory_structure(
                    os.path.join(base_dir, photo_type),
                    file_type,
                    year,
                    month
                )
            
            # Create final filename with date prefix if available
            if created_date:
                date_str = created_date.strftime("%Y%m%d_%H%M%S")
                filename = f"{date_str}_{filename}"
            
            filepath = os.path.join(photo_dir, filename)

            # --- Content-based deduplication logic ---
            if not hasattr(self, '_photo_hashes'):
                self._photo_hashes = set()
                # Optionally, load from a persistent file here

            def compute_sha256(file_path):
                hasher = hashlib.sha256()
                with open(file_path, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        hasher.update(chunk)
                return hasher.hexdigest()

            # Download to a temporary file first
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                download = photo.download()
                tmp_file.write(download.raw.read())
                tmp_file_path = tmp_file.name

            photo_hash = compute_sha256(tmp_file_path)
            if photo_hash in self._photo_hashes:
                logger.info(f"Duplicate photo detected by hash, skipping: {filepath}")
                os.remove(tmp_file_path)
                return False
            else:
                self._photo_hashes.add(photo_hash)
                # Move temp file to final location
                os.makedirs(photo_dir, exist_ok=True)
                if not os.path.exists(filepath):
                    os.rename(tmp_file_path, filepath)
                else:
                    # If file exists, add a suffix
                    base, ext = os.path.splitext(filepath)
                    i = 1
                    new_filepath = f"{base}_{i}{ext}"
                    while os.path.exists(new_filepath):
                        i += 1
                        new_filepath = f"{base}_{i}{ext}"
                    os.rename(tmp_file_path, new_filepath)
                    filepath = new_filepath

            # Handle metadata
            if self.config.get('options.preserve_metadata'):
                self.metadata.preserve_timestamps(filepath, created_date)
                self.metadata.save_exif_data(photo, filepath)
            
            # Handle Live Photos
            if self.config.get('options.handle_live_photos'):
                self._handle_live_photo(photo, filepath)
            
            logger.debug(f"Successfully downloaded: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing {photo.filename}: {str(e)}")
            return False
    
    def _get_photo_date(self, photo: Any) -> Tuple[Any, Any]:
        """Get the year and month for a photo.
        
        Args:
            photo: Photo object
            
        Returns:
            Tuple: Year and month
        """
        if hasattr(photo, 'created'):
            return photo.created.year, photo.created.month
        return "unknown_year", "unknown_month"
    
    def _handle_live_photo(self, photo: Any, photo_path: str) -> bool:
        """Handle Live Photo video components.
        
        Args:
            photo: Photo object
            photo_path: Path to the photo file
            
        Returns:
            bool: True if Live Photo was handled
        """
        try:
            if hasattr(photo, 'versions') and photo.versions:
                live_photo_video = None
                for version in photo.versions.values():
                    if version.get('type') == 'video':
                        live_photo_video = version
                        break
                
                if live_photo_video:
                    video_filename = os.path.splitext(
                        os.path.basename(photo_path)
                    )[0] + '.mov'
                    video_dir = os.path.join(
                        os.path.dirname(os.path.dirname(photo_path)),
                        'Videos'
                    )
                    os.makedirs(video_dir, exist_ok=True)
                    
                    video_path = os.path.join(video_dir, video_filename)
                    video_download = photo.download(version='video')
                    
                    with open(video_path, 'wb') as f:
                        f.write(video_download.raw.read())
                    
                    if hasattr(photo, 'created'):
                        self.metadata.preserve_timestamps(video_path, photo.created)
                    
                    logger.debug(f"Saved Live Photo video: {video_path}")
                    return True
                    
        except Exception as e:
            logger.warning(f"Could not process Live Photo: {str(e)}")
        
        return False
    
    def _update_stats(self, library_type: str, photo: Any,
                     album_name: Optional[str] = None) -> None:
        """Update download statistics.
        
        Args:
            library_type: Type of library
            photo: Downloaded photo
            album_name: Optional album name
        """
        if album_name:
            if "Shared_Albums" not in self.stats:
                self.stats["Shared_Albums"] = {}
            if album_name not in self.stats["Shared_Albums"]:
                self.stats["Shared_Albums"][album_name] = 0
            self.stats["Shared_Albums"][album_name] += 1
        else:
            year, month = self._get_photo_date(photo)
            file_type = get_file_type(photo.filename)
            
            if library_type not in self.stats:
                self.stats[library_type] = {}
            if file_type not in self.stats[library_type]:
                self.stats[library_type][file_type] = {}
            if year not in self.stats[library_type][file_type]:
                self.stats[library_type][file_type][year] = {}
            if month not in self.stats[library_type][file_type][year]:
                self.stats[library_type][file_type][year][month] = 0
            
            self.stats[library_type][file_type][year][month] += 1