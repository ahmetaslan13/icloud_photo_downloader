# iCloud Photo Downloader

A powerful and professional Python utility for downloading, organizing, and maintaining your iCloud photo library. This tool provides an efficient way to create well-organized local backups of your iCloud photos and videos while preserving all metadata and organization.

![License](https://img.shields.io/github/license/ahmetaslan13/icloud_photo_downloader)
![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)

## What is it?

iCloud Photo Downloader is a command-line tool that helps you:
- Download your entire iCloud photo library or selected portions
- Maintain an organized local backup of your photos and videos
- Preserve all metadata, including location data and timestamps
- Handle Live Photos and their video components
- Process shared albums and photos shared with you

## Key Features

### Smart Download Management
- **Comprehensive Download**: Downloads personal library, shared photos, and shared albums
- **Progress Tracking**: Real-time progress bars and download speed information
- **Resume Capability**: Can resume interrupted downloads
- **Duplicate Prevention**: Checks for existing files to avoid duplicates
- **Error Recovery**: Automatic retry for failed downloads

### Intelligent Organization
- **Structured Storage**: 
  - Organizes by media type (HEIC, JPEG, PNG, Videos, etc.)
  - Creates year/month folder hierarchy
  - Separate sections for personal and shared content
- **Smart Naming**:
  - Preserves original filenames
  - Adds date prefixes for easy sorting
  - Handles Live Photo pairs

### Media Support
- **Photos**: HEIC, JPEG, PNG, GIF
- **RAW Formats**: RAW, DNG, CR2, ARW
- **Videos**: MOV, MP4, M4V
- **Live Photos**: Maintains connection between photo and video components

### Data Preservation
- **Metadata Handling**:
  - Preserves EXIF data
  - Maintains creation dates
  - Keeps location information
  - Retains original timestamps
- **iCloud Compatibility**: 
  - Maintains format compatibility with iCloud
  - Preserves album organizations
  - Keeps shared photo relationships

### Security & Performance
- **Secure Authentication**:
  - Supports two-factor authentication (2FA)
  - Secure credential handling
  - No local credential storage
- **Resource Management**:
  - Disk space verification
  - Configurable concurrent downloads
  - Memory-efficient processing

## Installation

### Prerequisites

1. **Python Requirements**:
   - Python 3.6 or higher installed
     ```bash
     # Verify Python version
     python3 --version
     ```
   - pip (Python package installer)
     ```bash
     # Verify pip installation
     python3 -m pip --version
     ```

2. **Required Python Packages**:
   ```bash
   # For macOS/Linux:
   python3 -m pip install pyicloud Pillow piexif tqdm pyyaml

   # For Windows:
   python -m pip install pyicloud Pillow piexif tqdm pyyaml
   ```

3. **System Requirements**:
   - Internet connection
   - iCloud account with two-factor authentication enabled (recommended)
   - Sufficient disk space for your photo library (minimum 10GB recommended)

### Method 1: Using pip (Recommended)
```bash
pip install icloud-photo-downloader
```

### Method 2: From Source
```bash
# Clone the repository
git clone https://github.com/ahmetaslan13/icloud_photo_downloader.git

# Navigate to the project directory
cd icloud_photo_downloader

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## How to Use

### Basic Usage
```bash
icloud-photo-downloader
```
The tool will guide you through an interactive process to:
1. Enter your iCloud credentials
2. Handle two-factor authentication if needed
3. Select download location
4. Begin the download process

### Advanced Usage
```bash
# Specify custom output directory
icloud-photo-downloader --output ~/Pictures/iCloud

# Enable debug logging
icloud-photo-downloader --log-level DEBUG --log-file download.log

# Skip shared albums
icloud-photo-downloader --no-albums

# Skip photos shared with you
icloud-photo-downloader --no-shared

# Use custom configuration file
icloud-photo-downloader --config my_config.yml
```

### Configuration
You can customize the behavior by creating a `config.yml` file:
```yaml
download:
  default_path: "~/Pictures/iCloud_Photos"
  required_space_gb: 10
  create_timestamp_folder: true

options:
  download_shared: true
  download_albums: true
  preserve_metadata: true
  handle_live_photos: true

performance:
  max_retries: 3
  max_concurrent_downloads: 4

logging:
  level: "INFO"
  log_to_file: true
  log_file: "download.log"
```

## Results and Organization

### Directory Structure
Your media will be organized in a clean, hierarchical structure:

```
Download_YYYYMMDD_HHMMSS/
├── Personal/
│   ├── HEIC/
│   │   ├── 2023/
│   │   │   ├── 01-January/
│   │   │   │   ├── 20230101_123456_IMG_0001.HEIC
│   │   │   │   └── ...
│   │   │   └── 12-December/
│   │   └── 2024/
│   ├── JPEG/
│   ├── PNG/
│   ├── Videos/
│   ├── GIF/
│   └── RAW/
├── Shared_With_Me/
│   ├── HEIC/
│   ├── JPEG/
│   └── ...
└── Shared_Albums/
    ├── Album_Name_1/
    │   ├── 20230101_123456_IMG_0001.HEIC
    │   └── ...
    └── Album_Name_2/
```

### File Organization
- **Date-Based**: Files are organized by year and month
- **Type-Based**: Separated by file format (HEIC, JPEG, etc.)
- **Source-Based**: Personal photos, shared photos, and albums are separated
- **Naming Convention**: `YYYYMMDD_HHMMSS_ORIGINALNAME.EXT`

### Metadata Preservation
- Original creation dates
- GPS location data
- EXIF information
- Live Photo relationships
- Album organization

## Security and Privacy

### Credential Handling
- No local storage of credentials
- Secure authentication process
- Support for two-factor authentication
- Uses Apple's official API

### Data Protection
- Verifies downloads for integrity
- Preserves original file security attributes
- No modification of original content
- Optional encryption of local files

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

For major changes, please open an issue first to discuss what you would like to change.

## Support and Troubleshooting

### Common Issues
1. **Authentication Failed**: 
   - Verify your Apple ID and password
   - Ensure 2FA is handled correctly
   - Check internet connection

2. **Download Issues**:
   - Verify sufficient disk space
   - Check internet connection
   - Ensure iCloud Photos is enabled

3. **Organization Issues**:
   - Check write permissions
   - Verify disk space
   - Review configuration settings

### Getting Help
1. Check the [Issues](https://github.com/ahmetaslan13/icloud_photo_downloader/issues) page
2. Review closed issues for similar problems
3. Open a new issue with:
   - Detailed description
   - Error messages
   - System information
   - Steps to reproduce

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [pyicloud](https://github.com/picklepete/pyicloud) for iCloud connectivity
- [Pillow](https://python-pillow.org/) for image processing
- [piexif](https://github.com/hMatoba/Piexif) for EXIF handling