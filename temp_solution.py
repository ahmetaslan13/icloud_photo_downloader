#!/usr/bin/env python3
import os
import sys
from datetime import datetime
from pyicloud import PyiCloudService
import piexif
from PIL import Image
import shutil
import time
import calendar
import hashlib
import tempfile

def check_disk_space(directory, required_space_gb=10):
    """Check if there's enough space on the target drive."""
    try:
        total, used, free = shutil.disk_usage(directory)
        free_gb = free / (1024 * 1024 * 1024)  # Convert to GB
        
        if free_gb < required_space_gb:
            print(f"\nWARNING: Only {free_gb:.1f}GB free space available on the target drive.")
            response = input("Do you want to continue anyway? (y/n): ")
            if response.lower() != 'y':
                sys.exit(1)
        
        return free_gb
    except Exception as e:
        print(f"Error checking disk space: {str(e)}")
        return None


def get_download_path():
    """Get the download path from user input."""
    default_path = "/Volumes/T7/iCloud_Photos"
    
    print("\nWhere would you like to save the photos?")
    print(f"Default path: {default_path}")
    user_path = input("Press Enter to use default path or type a new path: ").strip()
    
    final_path = user_path if user_path else default_path
    
    # Check if the drive exists
    drive_path = os.path.dirname(final_path)
    if not os.path.exists(drive_path):
        print(f"Error: Drive {drive_path} not found!")
        sys.exit(1)
    
    # Check available space
    free_space = check_disk_space(drive_path)
    if free_space:
        print(f"\nAvailable space on target drive: {free_space:.1f}GB")
    
    return final_path

def authenticate_icloud():
    """Authenticate with iCloud."""
    print("Please enter your iCloud credentials:")
    apple_id = input("Apple ID (email): ")
    password = input("Password: ")
    
    try:
        api = PyiCloudService(apple_id, password)
        
        # Handle 2FA if needed
        if api.requires_2fa:
            print("Two-factor authentication required.")
            code = input("Enter the code you received: ")
            result = api.validate_2fa_code(code)
            print("2FA validation result:", result)
            
        return api
    except Exception as e:
        print(f"Authentication failed: {str(e)}")
        sys.exit(1)

def get_file_type_folder(filename):
    """Determine the appropriate folder based on file extension."""
    ext = os.path.splitext(filename)[1].lower()
    
    # Define file type categories
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

def get_location_name(photo):
    """Extract location name from photo metadata, including encrypted location data."""
    try:
        # First try the standard location attribute
        loc = getattr(photo, 'location', None)
        if loc:
            # If it's a dict
            if isinstance(loc, dict):
                lat = loc.get('latitude') or loc.get('lat')
                lon = loc.get('longitude') or loc.get('lon')
                if lat is not None and lon is not None:
                    lat_rounded = round(float(lat), 2)
                    lon_rounded = round(float(lon), 2)
                    return f"Lat{lat_rounded}_Lon{lon_rounded}"
            # If it's a tuple or list
            if isinstance(loc, (tuple, list)) and len(loc) == 2:
                lat, lon = loc
                if lat is not None and lon is not None:
                    lat_rounded = round(float(lat), 2)
                    lon_rounded = round(float(lon), 2)
                    return f"Lat{lat_rounded}_Lon{lon_rounded}"
            # If it's a nested dict (sometimes location['location'] = {...})
            if isinstance(loc, dict) and 'location' in loc:
                nested = loc['location']
                if isinstance(nested, dict):
                    lat = nested.get('latitude') or nested.get('lat')
                    lon = nested.get('longitude') or nested.get('lon')
                    if lat is not None and lon is not None:
                        lat_rounded = round(float(lat), 2)
                        lon_rounded = round(float(lon), 2)
                        return f"Lat{lat_rounded}_Lon{lon_rounded}"
        
        # If standard location is not available, try to extract from encrypted location data
        if hasattr(photo, '_asset_record'):
            asset_record = photo._asset_record
            if 'fields' in asset_record and 'locationEnc' in asset_record['fields']:
                try:
                    import base64
                    import plistlib
                    
                    location_enc = asset_record['fields']['locationEnc']['value']
                    decoded = base64.b64decode(location_enc)
                    plist_data = plistlib.loads(decoded)
                    
                    if isinstance(plist_data, dict):
                        lat = plist_data.get('lat')
                        lon = plist_data.get('lon')
                        if lat is not None and lon is not None:
                            lat_rounded = round(float(lat), 2)
                            lon_rounded = round(float(lon), 2)
                            return f"Lat{lat_rounded}_Lon{lon_rounded}"
                except Exception as e:
                    print(f"[DEBUG] Could not parse encrypted location for {getattr(photo, 'filename', 'unknown')}: {str(e)}")
        
        print(f"[DEBUG] No location data found for {getattr(photo, 'filename', 'unknown')}")
        return "Unknown_Location"
    except Exception as e:
        print(f"Warning: Could not extract location for {getattr(photo, 'filename', 'unknown')}: {str(e)}")
        return "Unknown_Location"

def create_location_year_directory(base_dir, location_name, year):
    """Create nested directories for location and year."""
    # Create location directory
    location_dir = os.path.join(base_dir, location_name)
    os.makedirs(location_dir, exist_ok=True)
    
    # Create year directory
    year_dir = os.path.join(location_dir, str(year))
    os.makedirs(year_dir, exist_ok=True)
    
    return year_dir

def create_type_year_directory(base_dir, file_type, year):
    """Create nested directories for file type and year only (months removed)."""
    type_dir = os.path.join(base_dir, file_type)
    os.makedirs(type_dir, exist_ok=True)
    year_dir = os.path.join(type_dir, str(year))
    os.makedirs(year_dir, exist_ok=True)
    return year_dir

def preserve_original_timestamps(filepath, created_date):
    """Preserve the original creation and modification dates of the file."""
    try:
        if created_date:
            timestamp = time.mktime(created_date.timetuple())
            os.utime(filepath, (timestamp, timestamp))
    except Exception as e:
        print(f"Warning: Could not preserve timestamps for {filepath}: {str(e)}")

def save_metadata(photo, filepath):
    """Save photo metadata in a way that's compatible with iCloud."""
    try:
        if filepath.lower().endswith(('.jpg', '.jpeg')):
            # Read existing EXIF data if present
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}}
            try:
                if os.path.exists(filepath):
                    img = Image.open(filepath)
                    if 'exif' in img.info:
                        exif_dict = piexif.load(img.info['exif'])
            except Exception:
                pass

            # Update creation date if available
            if hasattr(photo, 'created'):
                date_time = photo.created
                date_str = date_time.strftime("%Y:%m:%d %H:%M:%S")
                exif_dict["0th"][piexif.ImageIFD.DateTime] = date_str
                exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_str
                exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_str

            # Update GPS data if available
            if hasattr(photo, 'location') and photo.location:
                location = photo.location
                if 'latitude' in location and 'longitude' in location:
                    lat = location['latitude']
                    lon = location['longitude']
                    
                    exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = piexif.GPSHelper.deg_to_dms(abs(lat))
                    exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = piexif.GPSHelper.deg_to_dms(abs(lon))
                    exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = 'N' if lat >= 0 else 'S'
                    exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = 'E' if lon >= 0 else 'W'
            
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, filepath)
    except Exception as e:
        print(f"Warning: Could not save EXIF data for {filepath}: {str(e)}")

def handle_live_photo(photo, base_path, filename):
    """Handle Live Photo pairs to maintain compatibility."""
    try:
        if hasattr(photo, 'versions') and photo.versions:
            # Check if this is a Live Photo
            live_photo_video = None
            for version in photo.versions.values():
                if 'type' in version and version['type'] == 'video':
                    live_photo_video = version
                    break

            if live_photo_video:
                # Get the video component filename (usually .mov)
                video_filename = os.path.splitext(filename)[0] + '.mov'
                video_path = os.path.join(os.path.dirname(base_path), 'Videos', video_filename)
                
                # Ensure the Videos directory exists
                os.makedirs(os.path.dirname(video_path), exist_ok=True)
                
                # Download the video component
                video_download = photo.download(version='video')
                with open(video_path, 'wb') as f:
                    f.write(video_download.raw.read())
                
                # Preserve timestamps for the video component
                if hasattr(photo, 'created'):
                    preserve_original_timestamps(video_path, photo.created)
                
                return True
    except Exception as e:
        print(f"Warning: Could not process Live Photo components for {filename}: {str(e)}")
    
    return False

def check_icloud_photos_exists(photo, icloud_photos_path, current_download_dir):
    """Check if photo already exists in current download directory only."""
    try:
        if not current_download_dir or not os.path.exists(current_download_dir):
            return False, None
        
        # Get photo creation date for filename matching
        if hasattr(photo, 'created'):
            creation_date = photo.created
            date_str = creation_date.strftime("%Y%m%d_%H%M%S")
        else:
            date_str = "unknown_date"
        
        # Create expected filename
        expected_filename = f"{date_str}_{photo.filename}"
        
        # Search only in current download directory (not old download folders)
        for root, dirs, files in os.walk(current_download_dir):
            if expected_filename in files:
                return True, os.path.join(root, expected_filename)
        
        return False, None
    except Exception as e:
        print(f"Warning: Error checking current download directory: {str(e)}")
        return False, None

def compute_sha256(file_path):
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def process_photo(photo, base_dir, stats, photo_type="Personal", album_name=None, downloaded_photos=None, use_location_organization=False, existing_files=None, unique_photo_keys=None):
    """Process a single photo with full metadata preservation and robust uniqueness check."""
    try:
        if unique_photo_keys is None:
            unique_photo_keys = set()
        # Get photo creation date
        if hasattr(photo, 'created'):
            creation_date = photo.created
            year = creation_date.year
            date_str = creation_date.strftime("%Y%m%d_%H%M%S")
        else:
            year = "unknown_year"
            date_str = "unknown_date"
        # Get photo id
        photo_id = getattr(photo, 'id', None)
        # Keep original filename to maintain iCloud compatibility
        original_filename = photo.filename
        file_type = get_file_type_folder(original_filename)
        # Determine the appropriate directory structure
        if album_name:
            photo_dir = os.path.join(base_dir, "Shared_Albums", album_name)
            os.makedirs(photo_dir, exist_ok=True)
        else:
            if use_location_organization:
                location_name = get_location_name(photo)
                photo_dir = create_location_year_directory(
                    os.path.join(base_dir, photo_type),
                    location_name,
                    year
                )
            else:
                photo_dir = create_type_year_directory(
                    os.path.join(base_dir, photo_type),
                    file_type,
                    year
                )
        # Create filename that preserves original name but ensures uniqueness
        base_filename = f"{date_str}_{original_filename}"
        filename = base_filename
        filepath = os.path.join(photo_dir, filename)
        # Download the original photo to a temp file for hash/size check
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            download = photo.download()
            tmp_file.write(download.raw.read())
            tmp_file_path = tmp_file.name
        # Compute hash and size
        photo_hash = compute_sha256(tmp_file_path)
        photo_size = os.path.getsize(tmp_file_path)
        # Build uniqueness key
        unique_key = (photo_id, date_str, photo_hash, photo_size)
        if unique_key in unique_photo_keys:
            os.remove(tmp_file_path)
            return False, False, None
        unique_photo_keys.add(unique_key)
        # Handle filename conflicts by adding a counter
        counter = 1
        while os.path.exists(filepath):
            name, ext = os.path.splitext(base_filename)
            filename = f"{name}_{counter:03d}{ext}"
            filepath = os.path.join(photo_dir, filename)
            counter += 1
        rel_filepath = os.path.relpath(filepath, base_dir)
        # Move temp file to final location
        shutil.move(tmp_file_path, filepath)
        # Preserve original creation and modification dates
        if hasattr(photo, 'created'):
            preserve_original_timestamps(filepath, photo.created)
        # Save metadata for supported formats
        save_metadata(photo, filepath)
        # Handle Live Photos
        is_live_photo = handle_live_photo(photo, filepath, filename)
        # Update stats only for successful downloads
        if album_name:
            if "Shared_Albums" not in stats:
                stats["Shared_Albums"] = {}
            if album_name not in stats["Shared_Albums"]:
                stats["Shared_Albums"][album_name] = 0
            stats["Shared_Albums"][album_name] += 1
        else:
            if photo_type not in stats:
                stats[photo_type] = {}
            if file_type not in stats[photo_type]:
                stats[photo_type][file_type] = {}
            if year not in stats[photo_type][file_type]:
                stats[photo_type][file_type][year] = 0
            stats[photo_type][file_type][year] += 1
        return True, is_live_photo, filepath
    except Exception as e:
        print(f"Error processing photo {photo.filename}: {str(e)}")
        return False, False, None

def download_all_photos(api, output_dir, download_options, use_location_organization=False):
    """Download photos based on user preferences."""
    from datetime import datetime
    
    stats = {}
    total_downloaded = 0
    errors = 0
    skipped = 0
    
    # Track processed unique asset ids across all sections to avoid duplicates
    processed_ids = set()
    unique_photo_keys = set() # New set for robust uniqueness check
    
    def get_unique_photo_id(photo):
        """Return a stable unique id for an iCloud asset."""
        pid = getattr(photo, 'id', None)
        if pid:
            return pid
        # Fallback: filename + created timestamp
        created = getattr(photo, 'created', None)
        date_str = created.strftime("%Y%m%d_%H%M%S") if created else "unknown_date"
        return f"{date_str}_{getattr(photo, 'filename', 'unknown')}"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Create detailed log file
    log_file = os.path.join(output_dir, "download_progress_detailed.txt")
    entry_counter = 1
    
    def log_entry(message, level="INFO"):
        nonlocal entry_counter
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"{entry_counter:04d}- [{timestamp}] [{level}] {message}"
        print(log_line)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
        entry_counter += 1
    
    # Initialize log file
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write(f"iCloud Photo Downloader - Detailed Progress Log\n")
        f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
    
    log_entry("Starting download session - downloading all photos without duplicate checking")
    log_entry("All photos will be downloaded regardless of filename similarities")
    log_entry(f"Output directory: {output_dir}")
    log_entry(f"Location organization: {'Enabled' if use_location_organization else 'Disabled'}")
    log_entry(f"Download options: {download_options}")
    
    # 1. Download Personal Library
    if download_options['personal']:
        log_entry("=" * 60)
        log_entry("Starting Personal Library Download")
        log_entry("=" * 60)
        
        try:
            photos = api.photos.all
            total = len(photos)
            log_entry(f"Found {total:,} photos in personal library")
            log_entry("Progress format: [Current/Total] [Status] [Filename] → [Filepath]")
            log_entry("Directory layout: Personal/<TYPE>/<YEAR>/filename")
            
            for i, photo in enumerate(photos, 1):
                try:
                    uid = get_unique_photo_id(photo)
                    if uid in processed_ids:
                        skipped += 1
                        log_entry(f"[Personal] SKIP duplicate by id: {uid} ({getattr(photo, 'filename', 'unknown')})", "INFO")
                        continue
                    filename = getattr(photo, 'filename', 'unknown')
                    created = getattr(photo, 'created', None)
                    created_str = created.strftime("%Y-%m-%d %H:%M:%S") if created else "Unknown"
                    
                    log_entry(f"Processing photo {i:,}/{total:,}: {filename} (ID: {uid}, Created: {created_str})", "PROCESS")
                    
                    success, is_live, filepath = process_photo(photo, output_dir, stats, "Personal", None, None, use_location_organization, None, unique_photo_keys)
                    
                    if success:
                        processed_ids.add(uid)
                        total_downloaded += 1
                        file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
                        file_size_mb = file_size / (1024 * 1024)
                        
                        log_entry(f"✓ Downloaded: {filename} (ID: {uid}) → {filepath} ({file_size_mb:.2f} MB)", "SUCCESS")
                        
                        if is_live:
                            log_entry(f"  ↳ Live Photo video component saved", "INFO")
                    else:
                        errors += 1
                        log_entry(f"✗ Failed to download: {filename}", "ERROR")
                        
                    # Log progress every 100 photos
                    if i % 100 == 0:
                        log_entry(f"Progress update: {i:,}/{total:,} processed, {total_downloaded:,} downloaded, {errors:,} errors")
                        
                except Exception as e:
                    errors += 1
                    log_entry(f"✗ Error downloading personal photo {filename}: {str(e)}", "ERROR")
                    
        except Exception as e:
            log_entry(f"✗ Error accessing personal library: {str(e)}", "ERROR")
        
        log_entry(f"Personal Library Complete: Downloaded: {total_downloaded:,}, Errors: {errors:,}")
        log_entry("=" * 60)
    else:
        log_entry("Skipping Personal Library (not selected)")

    # 2. Download Shared Photos
    if download_options['shared']:
        log_entry("=" * 60)
        log_entry("Starting Photos Shared With You Download")
        log_entry("=" * 60)
        
        try:
            shared_photos = api.photos.shared.all
            if shared_photos:
                total = len(shared_photos)
                log_entry(f"Found {total:,} shared photos")
                log_entry("Directory layout: Shared_With_Me/<TYPE>/<YEAR>/filename")
                for i, photo in enumerate(shared_photos, 1):
                    try:
                        uid = get_unique_photo_id(photo)
                        if uid in processed_ids:
                            skipped += 1
                            log_entry(f"[Shared_With_Me] SKIP duplicate by id: {uid} ({getattr(photo, 'filename', 'unknown')})", "INFO")
                            continue
                        filename = getattr(photo, 'filename', 'unknown')
                        created = getattr(photo, 'created', None)
                        created_str = created.strftime("%Y-%m-%d %H:%M:%S") if created else "Unknown"
                        
                        log_entry(f"Processing shared photo {i:,}/{total:,}: {filename} (ID: {uid}, Created: {created_str})", "PROCESS")
                        
                        success, is_live, filepath = process_photo(photo, output_dir, stats, "Shared_With_Me", None, None, use_location_organization, None, unique_photo_keys)
                        
                        if success:
                            processed_ids.add(uid)
                            total_downloaded += 1
                            file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
                            file_size_mb = file_size / (1024 * 1024)
                            
                            log_entry(f"✓ Downloaded: {filename} (ID: {uid}) → {filepath} ({file_size_mb:.2f} MB)", "SUCCESS")
                            
                            if is_live:
                                log_entry(f"  ↳ Live Photo video component saved", "INFO")
                        else:
                            errors += 1
                            log_entry(f"✗ Failed to download: {filename}", "ERROR")
                            
                        # Log progress every 50 photos
                        if i % 50 == 0:
                            log_entry(f"Progress update: {i:,}/{total:,} processed, {total_downloaded:,} downloaded, {errors:,} errors")
                            
                    except Exception as e:
                        errors += 1
                        log_entry(f"✗ Error downloading shared photo {filename}: {str(e)}", "ERROR")
            else:
                log_entry("No shared photos found")
        except Exception as e:
            log_entry(f"✗ Error accessing shared photos: {str(e)}", "ERROR")
        
        log_entry(f"Shared Photos Complete: Downloaded: {total_downloaded:,}, Errors: {errors:,}")
        log_entry("=" * 60)
    else:
        log_entry("Skipping Photos Shared With You (not selected)")

    # 3. Download Shared Albums
    if download_options['albums']:
        log_entry("=" * 60)
        log_entry("Starting Shared Albums Download")
        log_entry("=" * 60)
        
        try:
            albums = api.photos.shared.albums
            if albums:
                log_entry(f"Found {len(albums)} shared albums")
                log_entry("Directory layout: Shared_Albums/<ALBUM>/<TYPE>/<YEAR>/filename")
                for album_idx, album in enumerate(albums, 1):
                    try:
                        album_name = album.name
                        photos = album.photos
                        total = len(photos)
                        log_entry(f"Processing album {album_idx}/{len(albums)}: '{album_name}' ({total:,} photos)")
                        
                        for i, photo in enumerate(photos, 1):
                            try:
                                uid = get_unique_photo_id(photo)
                                if uid in processed_ids:
                                    skipped += 1
                                    log_entry(f"[Shared_Albums] SKIP duplicate by id: {uid} ({getattr(photo, 'filename', 'unknown')})", "INFO")
                                    continue
                                filename = getattr(photo, 'filename', 'unknown')
                                created = getattr(photo, 'created', None)
                                created_str = created.strftime("%Y-%m-%d %H:%M:%S") if created else "Unknown"
                                
                                log_entry(f"Processing album photo {i:,}/{total:,}: {filename} (ID: {uid}, Created: {created_str})", "PROCESS")
                                
                                success, is_live, filepath = process_photo(photo, output_dir, stats, 
                                                                 "Shared_Albums", album_name, None, use_location_organization, None, unique_photo_keys)
                                if success:
                                    processed_ids.add(uid)
                                    total_downloaded += 1
                                    file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
                                    file_size_mb = file_size / (1024 * 1024)
                                    
                                    log_entry(f"✓ Downloaded: {filename} (ID: {uid}) → {filepath} ({file_size_mb:.2f} MB)", "SUCCESS")
                                    
                                    if is_live:
                                        log_entry(f"  ↳ Live Photo video component saved", "INFO")
                                else:
                                    errors += 1
                                    log_entry(f"✗ Failed to download: {filename}", "ERROR")
                                    
                                # Log progress every 25 photos
                                if i % 25 == 0:
                                    log_entry(f"Album progress: {i:,}/{total:,} processed, {total_downloaded:,} downloaded, {errors:,} errors")
                                    
                            except Exception as e:
                                errors += 1
                                log_entry(f"✗ Error downloading photo from album: {str(e)}", "ERROR")
                                
                        log_entry(f"Album '{album_name}' complete: {total:,} photos processed")
                        
                    except Exception as e:
                        log_entry(f"✗ Error processing album: {str(e)}", "ERROR")
            else:
                log_entry("No shared albums found")
        except Exception as e:
            log_entry(f"✗ Error accessing shared albums: {str(e)}", "ERROR")
        
        log_entry(f"Shared Albums Complete: Downloaded: {total_downloaded:,}, Errors: {errors:,}")
        log_entry("=" * 60)
    else:
        log_entry("Skipping Shared Albums (not selected)")

    # Final summary with detailed logging
    log_entry("=" * 80)
    log_entry("DOWNLOAD SESSION COMPLETE")
    log_entry("=" * 80)
    log_entry(f"Total files downloaded: {total_downloaded:,}")
    log_entry(f"Errors encountered: {errors:,}")
    log_entry(f"Total unique assets processed: {len(processed_ids):,}")
    log_entry(f"Skipped duplicates across sections: {skipped:,}")
    log_entry(f"Success rate: {(total_downloaded / (total_downloaded + errors) * 100):.1f}%" if (total_downloaded + errors) > 0 else "N/A")
    
    # Detailed statistics logging
    log_entry("=" * 60)
    log_entry("DETAILED STATISTICS")
    log_entry("=" * 60)
    
    # Print personal library stats
    if "Personal" in stats:
        log_entry("Personal Library Statistics:")
        for file_type, years in stats["Personal"].items():
            type_total = sum(years.values())
            log_entry(f"  {file_type}: {type_total:,} files")
            for year in sorted(years.keys()):
                year_total = years[year]
                log_entry(f"    {year}: {year_total:,} files")

    # Print shared photos stats
    if "Shared_With_Me" in stats:
        log_entry("Shared With Me Statistics:")
        for file_type, years in stats["Shared_With_Me"].items():
            type_total = sum(years.values())
            log_entry(f"  {file_type}: {type_total:,} files")
            for year in sorted(years.keys()):
                year_total = years[year]
                log_entry(f"    {year}: {year_total:,} files")

    # Print shared albums stats
    if "Shared_Albums" in stats:
        log_entry("Shared Albums Statistics:")
        for album_name, count in stats["Shared_Albums"].items():
            log_entry(f"  {album_name}: {count:,} files")
    
    # Final timestamp
    log_entry("=" * 80)
    log_entry(f"Download session ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_entry("=" * 80)
    
    # Also print summary to console
    print("\nDownload Summary:")
    print("================")
    print(f"Total files downloaded: {total_downloaded:,}")
    print(f"Errors encountered: {errors:,}")
    print(f"Total files processed: {total_downloaded + errors:,}")
    print(f"Detailed log saved to: {log_file}")

def get_photo_counts(api):
    """Get photo counts and album information from iCloud."""
    counts = {
        'personal': 0,
        'shared': 0,
        'albums': {},
        'total_album_photos': 0
    }
    
    print("\n📊 Analyzing your iCloud photo library...")
    
    # Count personal photos
    try:
        personal_photos = api.photos.all
        counts['personal'] = len(personal_photos)
        print(f"✅ Personal Library: {counts['personal']:,} photos")
    except Exception as e:
        print(f"❌ Error accessing personal library: {str(e)}")
    
    # Count shared photos
    try:
        shared_photos = api.photos.shared.all
        if shared_photos:
            counts['shared'] = len(shared_photos)
            print(f"✅ Photos Shared With You: {counts['shared']:,} photos")
        else:
            print("ℹ️  Photos Shared With You: 0 photos")
    except Exception as e:
        print(f"❌ Error accessing shared photos: {str(e)}")
    
    # Count shared albums
    try:
        albums = api.photos.shared.albums
        if albums:
            print(f"✅ Shared Albums: {len(albums)} albums")
            for album in albums:
                try:
                    album_name = album.name
                    album_photos = album.photos
                    photo_count = len(album_photos)
                    counts['albums'][album_name] = photo_count
                    counts['total_album_photos'] += photo_count
                    print(f"   📁 '{album_name}': {photo_count:,} photos")
                except Exception as e:
                    print(f"   ❌ Error accessing album '{album.name}': {str(e)}")
        else:
            print("ℹ️  Shared Albums: 0 albums")
    except Exception as e:
        print(f"❌ Error accessing shared albums: {str(e)}")
    
    # Show totals
    total_photos = counts['personal'] + counts['shared'] + counts['total_album_photos']
    print(f"\n📈 Total photos available: {total_photos:,}")
    print(f"   • Personal: {counts['personal']:,}")
    print(f"   • Shared: {counts['shared']:,}")
    print(f"   • Albums: {counts['total_album_photos']:,}")
    
    return counts

def get_organization_preference():
    """Get user preference for photo organization."""
    print("\n" + "="*50)
    print("📁 ORGANIZATION OPTIONS")
    print("="*50)
    print("How would you like to organize your photos?")
    print("1. By file type, year (e.g., HEIC/2025/)")
    print("2. By location and year (e.g., Lat40.71_Lon-74.01/2025/)")
    print("   Note: Photos without GPS data will go to 'Unknown_Location'")
    
    while True:
        choice = input("\nEnter your choice (1-2): ").strip()
        if choice in ['1', '2']:
            break
        print("Please enter a valid choice (1-2)")
    
    return choice == '2'  # True for location-based, False for type-based

def get_download_options(photo_counts):
    """Get user preferences for what to download."""
    print("\n" + "="*50)
    print("🎯 DOWNLOAD OPTIONS")
    print("="*50)
    print("What would you like to download?")
    print(f"1. Personal Library only ({photo_counts['personal']:,} photos)")
    print(f"2. Photos Shared With You only ({photo_counts['shared']:,} photos)")
    print(f"3. Shared Albums only ({photo_counts['total_album_photos']:,} photos)")
    print(f"4. All photos ({photo_counts['personal'] + photo_counts['shared'] + photo_counts['total_album_photos']:,} photos)")
    
    while True:
        choice = input("\nEnter your choice (1-4): ").strip()
        if choice in ['1', '2', '3', '4']:
            break
        print("Please enter a valid choice (1-4)")
    
    options = {
        '1': {'personal': True, 'shared': False, 'albums': False},
        '2': {'personal': False, 'shared': True, 'albums': False},
        '3': {'personal': False, 'shared': False, 'albums': True},
        '4': {'personal': True, 'shared': True, 'albums': True}
    }
    
    return options[choice]

def main():
    print("iCloud Complete Photo Downloader")
    print("===============================")
    print("This will download your iCloud photo library with options for:")
    print("1. Personal Library")
    print("2. Photos Shared With You")
    print("3. Shared Albums")
    print("\nAll photos will maintain their:")
    print("- Original filenames")
    print("- Creation dates")
    print("- Location data")
    print("- EXIF metadata")
    print("- Live Photo connections")
    
    # Get download location
    base_dir = get_download_path()
    
    # Authenticate
    api = authenticate_icloud()
    
    # Get photo counts and album information
    photo_counts = get_photo_counts(api)
    
    # Get organization preference
    use_location_organization = get_organization_preference()
    
    # Get download options based on available photos
    download_options = get_download_options(photo_counts)
    
    # Create output directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(base_dir, f"download_{timestamp}")
    
    print(f"\nMedia will be saved to: {output_dir}")
    print("\nDirectory structure will be:")
    print(f"{output_dir}/")
    
    if download_options['personal']:
        print("├── Personal/")
        if use_location_organization:
            print("│   ├── Lat40.71_Lon-74.01/")
            print("│   │   ├── 2025/")
            print("│   │   └── ...")
            print("│   ├── Lat37.77_Lon-122.42/")
            print("│   │   ├── 2025/")
            print("│   │   └── ...")
            print("│   ├── Unknown_Location/")
            print("│   │   └── ...")
        else:
            print("│   ├── HEIC/")
            print("│   │   ├── 2025/")
            print("│   │   └── ...")
            print("│   ├── JPEG/")
            print("│   └── ...")
    
    if download_options['shared']:
        print("├── Shared_With_Me/")
        if use_location_organization:
            print("│   ├── Lat40.71_Lon-74.01/")
            print("│   │   └── 2025/")
            print("│   └── ...")
        else:
            print("│   ├── HEIC/")
            print("│   ├── JPEG/")
            print("│   └── ...")
    
    if download_options['albums']:
        print("└── Shared_Albums/")
        print("    ├── [Album Name 1]/")
        print("    ├── [Album Name 2]/")
        print("    └── ...")
    
    # Confirm with user
    response = input("\nPress Enter to start download or 'n' to cancel: ")
    if response.lower() == 'n':
        print("Download cancelled.")
        sys.exit(0)
    
    # Download photos based on user selection
    download_all_photos(api, output_dir, download_options, use_location_organization)
    
    print("\nDownload completed!")
    print(f"All media files have been saved to: {output_dir}")
    print("\nImportant Notes:")
    print("1. All metadata has been preserved")
    print("2. Live Photos are saved as pairs (photo + video)")
    print("3. Original creation dates are maintained")
    print("4. Files are organized but will work perfectly when uploaded back to iCloud")

if __name__ == "__main__":
    main()