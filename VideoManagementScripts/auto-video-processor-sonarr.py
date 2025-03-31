#!/usr/bin/env python3
"""
Automated Video Processing Script with Sonarr Renaming

This script extends auto-video-processor.py by adding a final step to rename
the processed videos according to Sonarr naming conventions.

Usage:
    python auto-video-processor-sonarr.py [--video_dir VIDEO_DIR] [--extract_dir EXTRACT_DIR] 
                                         [--output_dir OUTPUT_DIR] [--dry_run] [--recursive]
                                         [--skip_rename] [--skip_extract] [--sonarr_format FORMAT]
                                         [--sonarr_url URL] [--api_key KEY]
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import time

# Import existing functionality from auto-video-processor
from auto_video_processor import (run_command, rename_video_files, extract_audio_and_subs,
                                 merge_video_audio_subs, fix_track_names, ensure_directories)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('auto_video_processor_sonarr.log')
    ]
)
logger = logging.getLogger('AutoVideoProcessorSonarr')

def rename_for_sonarr(output_dir, sonarr_format, recursive=False, dry_run=False, 
                     sonarr_url=None, api_key=None):
    """
    Run the sonarr-renamer.py script to rename processed files to Sonarr format
    
    Args:
        output_dir (str): Directory containing processed video files
        sonarr_format (str): Naming format to use
        recursive (bool): Whether to process subdirectories
        dry_run (bool): If True, only print commands without executing
        sonarr_url (str): Sonarr API URL for fetching episode information
        api_key (str): Sonarr API key
        
    Returns:
        bool: True if successful, False otherwise
    """
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sonarr-renamer.py')
    if not os.path.exists(script_path):
        logger.error(f"Required script not found: {script_path}")
        return False
    
    cmd = [
        sys.executable,
        script_path,
        '--input_dir', output_dir,
        '--naming_format', sonarr_format
    ]
    
    if recursive:
        cmd.append('--recursive')
    
    if dry_run:
        cmd.append('--dry_run')
    
    if sonarr_url:
        cmd.extend(['--sonarr_url', sonarr_url])
    
    if api_key:
        cmd.extend(['--api_key', api_key])
    
    return run_command(cmd, "Renaming to Sonarr format", dry_run)

def main():
    """Main function to run the extended automated video processing workflow"""
    parser = argparse.ArgumentParser(
        description='Automate video processing with Sonarr renaming'
    )
    
    # Define directories (same as original)
    parser.add_argument(
        '--video_dir', 
        help='Directory containing original video files',
        default='./Video'
    )
    parser.add_argument(
        '--extract_dir', 
        help='Directory for extracted audio and subtitle files',
        default='./Extracted'
    )
    parser.add_argument(
        '--output_dir', 
        help='Directory for merged output files',
        default='./Merged'
    )
    
    # Processing options (same as original)
    parser.add_argument(
        '--recursive', 
        action='store_true',
        help='Process video directories recursively'
    )
    parser.add_argument(
        '--dry_run', 
        action='store_true',
        help='Show commands without executing them'
    )
    parser.add_argument(
        '--skip_rename', 
        action='store_true',
        help='Skip the initial file renaming step'
    )
    parser.add_argument(
        '--skip_extract', 
        action='store_true',
        help='Skip the audio and subtitle extraction step'
    )
    
    # New Sonarr options
    parser.add_argument(
        '--sonarr_format',
        choices=['standard', 'standard_episode', 'scene', 'scene_episode', 'folder_season_episode', 'custom'],
        default='standard',
        help='Sonarr naming format to use'
    )
    parser.add_argument(
        '--custom_format',
        help='Custom naming format (used if --sonarr_format=custom)'
    )
    parser.add_argument(
        '--sonarr_url',
        help='Sonarr API URL (e.g., http://localhost:8989)'
    )
    parser.add_argument(
        '--api_key',
        help='Sonarr API key'
    )
    parser.add_argument(
        '--skip_sonarr_rename',
        action='store_true',
        help='Skip the Sonarr renaming step'
    )
    
    args = parser.parse_args()
    
    start_time = time.time()
    logger.info("-" * 80)
    logger.info("Starting automated video processing workflow with Sonarr renaming")
    
    # Ensure all required directories exist
    if not ensure_directories(args.video_dir, args.extract_dir, args.output_dir):
        logger.error("Failed to set up required directories. Exiting.")
        sys.exit(1)
    
    # Step 1: Rename original video files to follow standard format
    if not args.skip_rename:
        logger.info("Step 1: Renaming original video files")
        if not rename_video_files(args.video_dir, args.recursive, args.dry_run):
            logger.warning("File renaming had errors. Continuing with caution.")
    else:
        logger.info("Skipping file renaming step as requested")
    
    # Step 2: Extract audio and subtitle tracks
    if not args.skip_extract:
        logger.info("Step 2: Extracting audio and subtitle tracks")
        if not extract_audio_and_subs(args.video_dir, args.extract_dir, args.dry_run):
            logger.warning("Audio and subtitle extraction had errors. Continuing with caution.")
    else:
        logger.info("Skipping audio and subtitle extraction step as requested")
    
    # Step 3: Merge video with audio and subtitles
    logger.info("Step 3: Merging video with audio and subtitles")
    if not merge_video_audio_subs(args.video_dir, args.extract_dir, args.output_dir, args.dry_run):
        logger.error("Video merging failed. Exiting.")
        sys.exit(1)
    
    # Step 4: Fix track names in the merged files
    logger.info("Step 4: Fixing track names in merged files")
    if not fix_track_names(args.output_dir, args.dry_run):
        logger.warning("Track name fixing had errors.")
    
    # Step 5 (NEW): Rename for Sonarr compatibility
    if not args.skip_sonarr_rename:
        logger.info("Step 5: Renaming processed files to Sonarr format")
        
        # Handle custom format if specified
        sonarr_format = args.sonarr_format
        if sonarr_format == 'custom' and args.custom_format:
            sonarr_format = args.custom_format
        elif sonarr_format == 'custom' and not args.custom_format:
            logger.warning("Custom format specified but --custom_format not provided. Using 'standard' format.")
            sonarr_format = 'standard'
        
        # Run the Sonarr renamer
        if not rename_for_sonarr(
            args.output_dir, 
            sonarr_format, 
            args.recursive, 
            args.dry_run, 
            args.sonarr_url, 
            args.api_key
        ):
            logger.warning("Sonarr renaming had errors.")
    else:
        logger.info("Skipping Sonarr renaming step as requested")
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    logger.info(f"Automated video processing with Sonarr renaming completed in {elapsed_time:.2f} seconds")
    logger.info("-" * 80)

if __name__ == "__main__":
    main()