#!/usr/bin/env python3
"""
Script to remove PGS subtitles from MKV video files in the specified directory.
This script requires FFmpeg to be installed on your system.
"""

import os
import subprocess
import argparse
import logging
from pathlib import Path
import tempfile
import shutil

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_subtitle_info(input_file):
    """
    Get information about subtitle tracks in the video file.
    Returns a list of subtitle track IDs that are PGS format.
    """
    try:
        # Run ffprobe to get stream information
        cmd = [
            'ffprobe', 
            '-v', 'quiet', 
            '-print_format', 'json', 
            '-show_streams', 
            '-select_streams', 's', 
            input_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the JSON output to find PGS subtitle tracks
        import json
        data = json.loads(result.stdout)
        
        pgs_track_ids = []
        for stream in data.get('streams', []):
            codec_name = stream.get('codec_name', '').lower()
            index = stream.get('index')
            
            if codec_name in ['pgssub', 'hdmv_pgs_subtitle']:
                pgs_track_ids.append(index)
                
        return pgs_track_ids
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Error analyzing {input_file}: {e}")
        return []
    except json.JSONDecodeError:
        logger.error(f"Error parsing ffprobe output for {input_file}")
        return []

def remove_pgs_subtitles(input_file, output_dir=None, dry_run=False):
    """
    Remove PGS subtitles from an MKV file and save the result.
    If output_dir is None, it will replace the original file.
    """
    pgs_track_ids = get_subtitle_info(input_file)
    
    if not pgs_track_ids:
        logger.info(f"No PGS subtitles found in {input_file}")
        return False
    
    logger.info(f"Found PGS subtitle tracks {pgs_track_ids} in {input_file}")
    
    if dry_run:
        logger.info(f"DRY RUN: Would remove PGS subtitles from {input_file}")
        return True
    
    input_path = Path(input_file)
    
    # Determine output file path
    if output_dir:
        output_path = Path(output_dir) / input_path.name
    else:
        # Create a temporary file in the same directory
        temp_dir = tempfile.mkdtemp(dir=input_path.parent)
        output_path = Path(temp_dir) / f"temp_{input_path.name}"
    
    # Create mapping file for subtitle tracks to remove
    mapping_args = []
    
    # Map all streams except PGS subtitle tracks
    mapping_args.extend(['-map', '0'])
    for track_id in pgs_track_ids:
        mapping_args.extend(['-map', f'-0:{track_id}'])
    
    # Run FFmpeg to copy all streams except the PGS subtitle tracks
    cmd = [
        'ffmpeg',
        '-i', str(input_path),
        *mapping_args,
        '-c', 'copy',  # Copy all streams without re-encoding
        str(output_path)
    ]
    
    try:
        logger.info(f"Processing {input_file}...")
        subprocess.run(cmd, check=True, capture_output=True)
        
        # If output_dir is None, replace the original file
        if not output_dir:
            shutil.move(str(output_path), str(input_path))
            # Clean up the temporary directory
            shutil.rmtree(temp_dir)
        
        logger.info(f"Successfully removed PGS subtitles from {input_file}")
        return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Error processing {input_file}: {e.stderr.decode() if e.stderr else str(e)}")
        # Clean up the temporary directory if it exists
        if not output_dir and 'temp_dir' in locals():
            shutil.rmtree(temp_dir)
        return False

def process_directory(directory, output_dir=None, dry_run=False):
    """
    Process all MKV files in the specified directory.
    """
    directory_path = Path(directory)
    
    # Create output directory if it doesn't exist
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Get all MKV files in the directory
    mkv_files = list(directory_path.glob('*.mkv'))
    
    if not mkv_files:
        logger.warning(f"No MKV files found in {directory}")
        return
    
    logger.info(f"Found {len(mkv_files)} MKV files in {directory}")
    
    success_count = 0
    for file_path in mkv_files:
        if remove_pgs_subtitles(str(file_path), output_dir, dry_run):
            success_count += 1
    
    logger.info(f"Successfully processed {success_count}/{len(mkv_files)} files")

def main():
    parser = argparse.ArgumentParser(description='Remove PGS subtitles from MKV files')
    parser.add_argument('directory', help='Directory containing MKV files')
    parser.add_argument('--output-dir', help='Output directory for processed files (if not specified, original files will be replaced)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without actually modifying files')
    
    args = parser.parse_args()
    
    logger.info("Starting PGS subtitle removal script")
    
    if args.dry_run:
        logger.info("DRY RUN MODE: No files will be modified")
    
    process_directory(args.directory, args.output_dir, args.dry_run)
    
    logger.info("Script completed")

if __name__ == "__main__":
    main()