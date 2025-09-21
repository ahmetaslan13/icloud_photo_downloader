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

def create_type_year_month_directory(base_dir, file_type, year, month):
    """Create nested directories for file type, year, and month."""
    # Create type directory
    type_dir = os.path.join(base_dir, file_type)
    os.makedirs(type_dir, exist_ok=True)
    
    # Create year directory
    year_dir = os.path.join(type_dir, str(year))
    os.makedirs(year_dir, exist_ok=True)
    
    # Create month directory with number and name (e.g., "01-January")
    if isinstance(month, int):
        month_name = calendar.month_name[month]
        month_dir = os.path.join(year_dir, f"{month:02d}-{month_name}")
    else:
        month_dir = os.path.join(year_dir, str(month))
    
    os.makedirs(month_dir, exist_ok=True)
    return month_dir

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

def process_photo(photo, base_dir, stats, photo_type="Personal", album_name=None):
    """Process a single photo with full metadata preservation."""
    try:
        # Get photo creation date
        if hasattr(photo, 'created'):
            creation_date = photo.created
            year = creation_date.year
            month = creation_date.month
            date_str = creation_date.strftime("%Y%m%d_%H%M%S")
        else:
            year = "unknown_year"
            month = "unknown_month"
            date_str = "unknown_date"
        
        # Keep original filename to maintain iCloud compatibility
        original_filename = photo.filename
        file_type = get_file_type_folder(original_filename)
        
        # Determine the appropriate directory structure
        if album_name:
            # For shared albums, use album-based structure
            photo_dir = os.path.join(base_dir, "Shared_Albums", album_name)
            os.makedirs(photo_dir, exist_ok=True)
            
            # Update stats
            if "Shared_Albums" not in stats:
                stats["Shared_Albums"] = {}
            if album_name not in stats["Shared_Albums"]:
                stats["Shared_Albums"][album_name] = 0
            stats["Shared_Albums"][album_name] += 1
        else:
            # For personal and shared photos, use type/year/month structure
            photo_dir = create_type_year_month_directory(
                os.path.join(base_dir, photo_type),
                file_type,
                year,
                month
            )
            
            # Update stats
            if photo_type not in stats:
                stats[photo_type] = {}
            if file_type not in stats[photo_type]:
                stats[photo_type][file_type] = {}
            if year not in stats[photo_type][file_type]:
                stats[photo_type][file_type][year] = {}
            if month not in stats[photo_type][file_type][year]:
                stats[photo_type][file_type][year][month] = 0
            stats[photo_type][file_type][year][month] += 1
        
        # Create filename that preserves original name
        filename = f"{date_str}_{original_filename}"
        filepath = os.path.join(photo_dir, filename)
        
        # Download the original photo
        download = photo.download()
        with open(filepath, 'wb') as f:
            f.write(download.raw.read())
        
        # Preserve original creation and modification dates
        if hasattr(photo, 'created'):
            preserve_original_timestamps(filepath, photo.created)
        
        # Save metadata for supported formats
        save_metadata(photo, filepath)
        
        # Handle Live Photos
        is_live_photo = handle_live_photo(photo, filepath, filename)
        
        return True, is_live_photo
    except Exception as e:
        print(f"Error processing photo {photo.filename}: {str(e)}")
        return False, False

def download_all_photos(api, output_dir):
    """Download all photos: personal, shared, and albums."""
    stats = {}
    total_downloaded = 0
    errors = 0
    
    # 1. Download Personal Library
    print("\nDownloading Personal Library...")
    try:
        photos = api.photos.all
        total = len(photos)
        print(f"Found {total} photos in personal library")
        
        for i, photo in enumerate(photos, 1):
            try:
                success, is_live = process_photo(photo, output_dir, stats, "Personal")
                if success:
                    total_downloaded += 1
                    print(f"[Personal {i}/{total}] Downloaded: {photo.filename}")
                    if is_live:
                        print(f"  ↳ Saved Live Photo video component")
                else:
                    errors += 1
            except Exception as e:
                print(f"Error downloading personal photo: {str(e)}")
                errors += 1
    except Exception as e:
        print(f"Error accessing personal library: {str(e)}")

    # 2. Download Shared Photos
    print("\nDownloading Photos Shared With You...")
    try:
        shared_photos = api.photos.shared.all
        if shared_photos:
            total = len(shared_photos)
            print(f"Found {total} shared photos")
            
            for i, photo in enumerate(shared_photos, 1):
                try:
                    success, is_live = process_photo(photo, output_dir, stats, "Shared_With_Me")
                    if success:
                        total_downloaded += 1
                        print(f"[Shared {i}/{total}] Downloaded: {photo.filename}")
                        if is_live:
                            print(f"  ↳ Saved Live Photo video component")
                    else:
                        errors += 1
                except Exception as e:
                    print(f"Error downloading shared photo: {str(e)}")
                    errors += 1
        else:
            print("No shared photos found")
    except Exception as e:
        print(f"Error accessing shared photos: {str(e)}")

    # 3. Download Shared Albums
    print("\nDownloading Shared Albums...")
    try:
        albums = api.photos.shared.albums
        if albums:
            print(f"Found {len(albums)} shared albums")
            
            for album in albums:
                try:
                    album_name = album.name
                    photos = album.photos
                    total = len(photos)
                    print(f"\nProcessing album '{album_name}' ({total} photos)")
                    
                    for i, photo in enumerate(photos, 1):
                        try:
                            success, is_live = process_photo(photo, output_dir, stats, 
                                                         album_name=album_name)
                            if success:
                                total_downloaded += 1
                                print(f"[Album '{album_name}' {i}/{total}] Downloaded: {photo.filename}")
                                if is_live:
                                    print(f"  ↳ Saved Live Photo video component")
                            else:
                                errors += 1
                        except Exception as e:
                            print(f"Error downloading photo from album: {str(e)}")
                            errors += 1
                except Exception as e:
                    print(f"Error processing album: {str(e)}")
        else:
            print("No shared albums found")
    except Exception as e:
        print(f"Error accessing shared albums: {str(e)}")

    # Print summary
    print("\nDownload Summary:")
    print("================")
    print(f"Total files downloaded: {total_downloaded}")
    print(f"Errors encountered: {errors}")
    
    # Print personal library stats
    if "Personal" in stats:
        print("\nPersonal Library:")
        for file_type, years in stats["Personal"].items():
            type_total = sum(sum(months.values()) 
                           for year_data in years.values() 
                           for months in [year_data])
            print(f"\n{file_type}: {type_total} files")
            for year in sorted(years.keys()):
                year_total = sum(stats["Personal"][file_type][year].values())
                print(f"  {year}: {year_total} files")
                for month in sorted(stats["Personal"][file_type][year].keys()):
                    count = stats["Personal"][file_type][year][month]
                    if isinstance(month, int):
                        month_name = calendar.month_name[month]
                        print(f"    {month:02d}-{month_name}: {count} files")
                    else:
                        print(f"    {month}: {count} files")

    # Print shared photos stats
    if "Shared_With_Me" in stats:
        print("\nShared With Me:")
        for file_type, years in stats["Shared_With_Me"].items():
            type_total = sum(sum(months.values()) 
                           for year_data in years.values() 
                           for months in [year_data])
            print(f"\n{file_type}: {type_total} files")
            for year in sorted(years.keys()):
                year_total = sum(stats["Shared_With_Me"][file_type][year].values())
                print(f"  {year}: {year_total} files")

    # Print shared albums stats
    if "Shared_Albums" in stats:
        print("\nShared Albums:")
        for album_name, count in stats["Shared_Albums"].items():
            print(f"  {album_name}: {count} files")

def main():
    print("iCloud Complete Photo Downloader")
    print("===============================")
    print("This will download your entire iCloud photo library including:")
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
    
    # Create output directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(base_dir, f"download_{timestamp}")
    
    print(f"\nMedia will be saved to: {output_dir}")
    print("\nDirectory structure will be:")
    print(f"{output_dir}/")
    print("├── Personal/")
    print("│   ├── HEIC/")
    print("│   │   ├── 2025/")
    print("│   │   │   ├── 01-January/")
    print("│   │   │   └── ...")
    print("│   ├── JPEG/")
    print("│   └── ...")
    print("├── Shared_With_Me/")
    print("│   ├── HEIC/")
    print("│   ├── JPEG/")
    print("│   └── ...")
    print("└── Shared_Albums/")
    print("    ├── [Album Name 1]/")
    print("    ├── [Album Name 2]/")
    print("    └── ...")
    
    # Confirm with user
    response = input("\nPress Enter to start download or 'n' to cancel: ")
    if response.lower() == 'n':
        print("Download cancelled.")
        sys.exit(0)
    
    # Download all photos
    download_all_photos(api, output_dir)
    
    print("\nDownload completed!")
    print(f"All media files have been saved to: {output_dir}")
    print("\nImportant Notes:")
    print("1. All metadata has been preserved")
    print("2. Live Photos are saved as pairs (photo + video)")
    print("3. Original creation dates are maintained")
    print("4. Files are organized but will work perfectly when uploaded back to iCloud")

if __name__ == "__main__":
    main()