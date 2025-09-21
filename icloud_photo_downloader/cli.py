"""Command line interface for iCloud Photo Downloader."""

import os
import sys
import logging
import argparse
from typing import Optional
from ..core.downloader import PhotoDownloader

def setup_logging(log_level: str, log_file: Optional[str] = None) -> None:
    """Set up logging configuration.
    
    Args:
        log_level: Desired logging level
        log_file: Optional path to log file
    """
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if requested
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Download and organize your iCloud photos"
    )
    
    parser.add_argument(
        '-c', '--config',
        help='Path to custom configuration file'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Custom output directory'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Set the logging level'
    )
    
    parser.add_argument(
        '--log-file',
        help='Save logs to a file'
    )
    
    parser.add_argument(
        '--no-albums',
        action='store_true',
        help='Skip downloading shared albums'
    )
    
    parser.add_argument(
        '--no-shared',
        action='store_true',
        help='Skip downloading photos shared with you'
    )
    
    return parser.parse_args()

def main() -> None:
    """Main entry point for the command line interface."""
    try:
        # Parse arguments
        args = parse_args()
        
        # Setup logging
        setup_logging(args.log_level, args.log_file)
        logger = logging.getLogger(__name__)
        
        # Create downloader instance
        downloader = PhotoDownloader(args.config)
        
        # Override config with command line arguments
        if args.output:
            downloader.config.set('download.default_path', args.output)
        if args.no_albums:
            downloader.config.set('options.download_albums', False)
        if args.no_shared:
            downloader.config.set('options.download_shared', False)
        
        # Get credentials
        print("\niCloud Photo Downloader")
        print("=====================")
        apple_id = input("Enter your Apple ID (email): ")
        password = input("Enter your password: ")
        
        # Start download
        downloader.start(apple_id, password)
        
    except KeyboardInterrupt:
        logger.info("\nDownload interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()