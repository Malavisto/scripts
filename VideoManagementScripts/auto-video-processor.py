#!/usr/bin/env python3
"""
Automated Video Processing Script

This script automates the process of:
1. Renaming original video files according to standardized patterns
2. Extracting audio and subtitle tracks 
3. Merging video files with audio and subtitle tracks
4. Standardizing track names in the merged files

It leverages the existing scripts in the VideoManagementScripts collection.

Usage:
    python auto-video-processor.py [--video_dir VIDEO_DIR] [--extract_dir EXTRACT_DIR] 
                                  [--output_dir OUTPUT_DIR] [--dry_run] [--recursive]
                                  [--skip_rename] [--skip_extract]
"""

import os
import sys
import argparse
import subprocess
import shutil
from pathlib import Path
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('auto_video_processor.log')
    ]
)
logger = logging.getLogger('AutoVideoProcessor')

def run_command(cmd, description, dry_run=False):
    """
    Run a shell command and log the output
    
    Args:
        cmd (list): Command to run as a list of arguments
        description (str): Description of what the command does
        dry_run (bool): If True, only print the command without executing
        
    Returns:
        bool: True if successful, False otherwise
    """
    cmd_str = " ".join(str(arg) for arg in cmd)
    
    if dry_run:
        logger.info(f"[DRY RUN] Would execute: {cmd_str}")
        return True
    
    logger.info(f"Executing: {description}")
    logger.debug(f"Command: {cmd_str}")
    
    try:
        result = subprocess.run(
            cmd, 
            check=True, 
            capture_output=True, 
            text=True
        )
        if result.stdout:
            logger.debug(f"STDOUT: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running {description}: Exit code {e.returncode}")
        logger.error(f"STDERR: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error running {description}: {str(e)}")
        return False

def rename_video_files(input_dir, recursive=False, dry_run=False):
    """
    Run the file-renamer.py script to rename video files according to standard format
    
    Args:
        input_dir (str): Directory containing video files to rename
        recursive (bool): Whether to process subdirectories
        dry_run (bool): If True, only print the commands without executing
        
    Returns:
        bool: True if successful, False otherwise
    """
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'file-renamer.py')
    if not os.path.exists(script_path):
        logger.error(f"Required script not found: {script_path}")
        return False
    
    cmd = [
        sys.executable,
        script_path,
        input_dir
    ]
    
    if recursive:
        cmd.append('--recursive')
    
    if dry_run:
        cmd.append('--dry-run')
    
    return run_command(cmd, "Renaming original video files", dry_run)

def extract_audio_and_subs(video_dir, extract_dir, dry_run=False):
    """
    Extract audio and subtitle tracks from video files
    
    Args:
        video_dir (str): Directory containing original video files
        extract_dir (str): Directory to save extracted streams
        dry_run (bool): If True, only print the commands without executing
        
    Returns:
        bool: True if successful, False otherwise
    """
    # We'll use video-extract.py if it exists, otherwise implement extraction logic here
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'video-extract.py')
    if os.path.exists(script_path):
        cmd = [
            sys.executable,
            script_path,
            video_dir,
            '--output_folder', extract_dir
        ]
        
        return run_command(cmd, "Extracting audio and subtitles", dry_run)
    else:
        logger.warning("video-extract.py not found. Skipping extraction step.")
        logger.warning("Please extract audio and subtitles manually before merging.")
        return True

def merge_video_audio_subs(video_dir, extract_dir, output_dir, dry_run=False):
    """
    Run the video-extract-merge.py script to merge videos with audio and subtitles
    
    Args:
        video_dir (str): Directory containing original video files
        extract_dir (str): Directory containing extracted audio and subtitle files
        output_dir (str): Directory to save the merged output files
        dry_run (bool): If True, only print the commands without executing
        
    Returns:
        bool: True if successful, False otherwise
    """
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'video-extract-merge.py')
    if not os.path.exists(script_path):
        logger.error(f"Required script not found: {script_path}")
        return False
    
    cmd = [
        sys.executable,
        script_path,
        '--video_dir', video_dir,
        '--extract_dir', extract_dir,
        '--output_dir', output_dir
    ]
    
    return run_command(cmd, "Merging video with audio and subtitles", dry_run)

def fix_track_names(input_dir, dry_run=False):
    """
    Run the track-name-fixer.py script to standardize track names
    
    Args:
        input_dir (str): Directory containing MKV files to process
        dry_run (bool): If True, only print the commands without executing
        
    Returns:
        bool: True if successful, False otherwise
    """
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'track-name-fixer.py')
    if not os.path.exists(script_path):
        logger.error(f"Required script not found: {script_path}")
        return False
    
    cmd = [
        sys.executable,
        script_path,
        '--input_dir', input_dir
    ]
    
    if dry_run:
        cmd.append('--dry-run')
    
    return run_command(cmd, "Fixing track names", dry_run)

def ensure_directories(video_dir, extract_dir, output_dir):
    """
    Ensure that all required directories exist, creating them if necessary
    
    Args:
        video_dir (str): Directory containing original video files
        extract_dir (str): Directory for extracted audio and subtitle files
        output_dir (str): Directory for merged output files
        
    Returns:
        bool: True if all directories exist or were created, False otherwise
    """
    try:
        # Verify video directory exists
        video_path = Path(video_dir).resolve()
        if not video_path.exists():
            logger.error(f"Video directory does not exist: {video_dir}")
            return False
        
        # Create extract directory if it doesn't exist
        extract_path = Path(extract_dir).resolve()
        if not extract_path.exists():
            logger.info(f"Creating extraction directory: {extract_dir}")
            extract_path.mkdir(parents=True, exist_ok=True)
        
        # Create output directory if it doesn't exist
        output_path = Path(output_dir).resolve()
        if not output_path.exists():
            logger.info(f"Creating output directory: {output_dir}")
            output_path.mkdir(parents=True, exist_ok=True)
        
        return True
    except Exception as e:
        logger.error(f"Error setting up directories: {str(e)}")
        return False

def main():
    """Main function to run the automated video processing workflow"""
    parser = argparse.ArgumentParser(
        description='Automate video processing: rename, extract, merge, and fix track names'
    )
    
    # Define directories
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
    
    # Processing options
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
    
    args = parser.parse_args()
    
    start_time = time.time()
    logger.info("-" * 80)
    logger.info("Starting automated video processing workflow")
    
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
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    logger.info(f"Automated video processing completed in {elapsed_time:.2f} seconds")
    logger.info("-" * 80)

if __name__ == "__main__":
    main()
