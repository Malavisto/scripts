#!/usr/bin/env python3
"""
Sonarr Compatible Video Renamer

This script renames video files produced by the auto-video-processor.py script to match 
Sonarr's naming conventions. It can be run as a post-processing step to ensure videos 
are properly recognized by Sonarr.

Usage:
    python sonarr-renamer.py --input_dir INPUT_DIR [--naming_format NAMING_FORMAT]
                             [--dry_run] [--recursive] [--api_key API_KEY] [--sonarr_url SONARR_URL]
"""

import os
import re
import argparse
import logging
import requests
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sonarr_renamer.log')
    ]
)
logger = logging.getLogger('SonarrRenamer')

# Sonarr naming format templates
SONARR_FORMATS = {
    "standard": "{Series Title} - S{season:02d}E{episode:02d}",
    "standard_episode": "{Series Title} - S{season:02d}E{episode:02d} - {Episode Title}",
    "scene": "{Series.Title}.S{season:02d}E{episode:02d}",
    "scene_episode": "{Series.Title}.S{season:02d}E{episode:02d}.{Episode.Title}",
    "folder_season_episode": "{Series Title}/Season {season}/S{season:02d}E{episode:02d} - {Episode Title}"
}

def get_file_info(file_path):
    """
    Get information from a video file using the existing naming pattern
    
    Args:
        file_path (str): Path to the video file
        
    Returns:
        dict: Information extracted from the filename
    """
    filename = os.path.basename(file_path)
    
    # Current pattern is ShowName_SxxExx_CODEC.ext
    pattern = re.compile(r'(.+?)_S(\d{2})E(\d{2})_(\w+)(\.\w+)$')
    match = pattern.match(filename)
    
    if match:
        show_name = match.group(1).replace('_', ' ')
        season = int(match.group(2))
        episode = int(match.group(3))
        codec = match.group(4)
        extension = match.group(5)
        
        return {
            'show_name': show_name,
            'season': season,
            'episode': episode,
            'codec': codec,
            'extension': extension
        }
    
    logger.warning(f"Could not parse filename: {filename}")
    return None

def get_episode_info_from_sonarr(sonarr_url, api_key, show_name, season, episode):
    """
    Get episode information from Sonarr API
    
    Args:
        sonarr_url (str): Base URL for Sonarr API
        api_key (str): Sonarr API key
        show_name (str): Name of the show
        season (int): Season number
        episode (int): Episode number
        
    Returns:
        dict: Episode information from Sonarr or None if not found
    """
    if not sonarr_url or not api_key:
        return None
    
    # First, find the series ID
    try:
        headers = {
            'X-Api-Key': api_key
        }
        
        # Get all series
        series_response = requests.get(f"{sonarr_url.rstrip('/')}/api/v3/series", headers=headers)
        series_response.raise_for_status()
        
        series_list = series_response.json()
        series_id = None
        
        # Find matching series (simple string match, could be improved)
        for series in series_list:
            if show_name.lower() in series['title'].lower():
                series_id = series['id']
                break
        
        if not series_id:
            logger.warning(f"Could not find series '{show_name}' in Sonarr")
            return None
        
        # Get episodes for the series
        episode_response = requests.get(
            f"{sonarr_url.rstrip('/')}/api/v3/episode", 
            params={'seriesId': series_id},
            headers=headers
        )
        episode_response.raise_for_status()
        
        episodes = episode_response.json()
        
        # Find matching episode
        for ep in episodes:
            if ep['seasonNumber'] == season and ep['episodeNumber'] == episode:
                return {
                    'title': ep['title'],
                    'series_title': series['title'],
                    'absolute_episode_number': ep.get('absoluteEpisodeNumber')
                }
        
        logger.warning(f"Could not find S{season:02d}E{episode:02d} for '{show_name}' in Sonarr")
        return None
    
    except requests.RequestException as e:
        logger.error(f"Error contacting Sonarr API: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting episode info: {str(e)}")
        return None

def format_filename(info, naming_format, episode_title=None):
    """
    Format a filename according to the specified naming format
    
    Args:
        info (dict): File information
        naming_format (str): Format string or key from SONARR_FORMATS
        episode_title (str, optional): Episode title from Sonarr
        
    Returns:
        str: Formatted filename
    """
    # Get the actual format string
    format_string = SONARR_FORMATS.get(naming_format, naming_format)
    
    # Default values
    series_title = info['show_name']
    season = info['season']
    episode = info['episode']
    extension = info['extension']
    
    # Replace common format variables
    result = format_string
    
    # Handle dot-separated format strings
    if '.Title' in format_string or '.Name' in format_string:
        series_dot = series_title.replace(' ', '.')
        result = result.replace('{Series.Title}', series_dot)
        
        if episode_title:
            episode_dot = episode_title.replace(' ', '.')
            result = result.replace('{Episode.Title}', episode_dot)
    else:
        result = result.replace('{Series Title}', series_title)
        
        if episode_title:
            result = result.replace('{Episode Title}', episode_title)
    
    # Replace season and episode
    result = result.format(season=season, episode=episode)
    
    # Add codec for quality identification (if desired)
    if '{codec}' in result:
        result = result.replace('{codec}', info['codec'])
    
    # Ensure filename is valid
    result = re.sub(r'[<>:"/\\|?*]', '', result)
    
    # Add file extension
    if not result.endswith(extension):
        result += extension
    
    return result

def rename_for_sonarr(input_dir, naming_format='standard', recursive=False, 
                     dry_run=False, sonarr_url=None, api_key=None):
    """
    Rename video files to match Sonarr naming conventions
    
    Args:
        input_dir (str): Directory containing video files to rename
        naming_format (str): Format to use for renaming
        recursive (bool): Whether to process subdirectories
        dry_run (bool): If True, only show what would be renamed without actually renaming
        sonarr_url (str): Sonarr API URL for fetching episode information
        api_key (str): Sonarr API key
        
    Returns:
        int: Number of files renamed
    """
    input_path = Path(input_dir)
    if not input_path.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        return 0
    
    # Video file extensions
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    
    # Collect all files to process
    files_to_process = []
    
    if recursive:
        for file_path in input_path.glob('**/*'):
            if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                files_to_process.append(file_path)
    else:
        for file_path in input_path.glob('*'):
            if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                files_to_process.append(file_path)
    
    renamed_count = 0
    
    # Process files
    for file_path in files_to_process:
        file_info = get_file_info(str(file_path))
        
        if not file_info:
            continue
        
        # Try to get episode title from Sonarr
        episode_info = None
        if sonarr_url and api_key:
            episode_info = get_episode_info_from_sonarr(
                sonarr_url, 
                api_key, 
                file_info['show_name'], 
                file_info['season'], 
                file_info['episode']
            )
        
        # Format new filename
        episode_title = episode_info['title'] if episode_info else None
        new_filename = format_filename(file_info, naming_format, episode_title)
        
        # Handle folder structure if needed
        if "folder_season" in naming_format:
            season_folder = file_path.parent / f"Season {file_info['season']}"
            if not season_folder.exists() and not dry_run:
                season_folder.mkdir(parents=True, exist_ok=True)
            new_file_path = season_folder / new_filename
        else:
            new_file_path = file_path.parent / new_filename
        
        # Handle name conflicts
        counter = 1
        original_new_path = new_file_path
        while new_file_path.exists() and new_file_path != file_path and not dry_run:
            name = original_new_path.stem
            suffix = original_new_path.suffix
            new_file_path = original_new_path.with_name(f"{name} ({counter}){suffix}")
            counter += 1
        
        # Rename the file
        if dry_run:
            logger.info(f"Would rename: \n  {file_path.name} \n  -> {new_file_path.name}")
        else:
            if new_file_path != file_path:
                try:
                    # Create parent directories if they don't exist
                    new_file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Rename the file
                    file_path.rename(new_file_path)
                    logger.info(f"Renamed: \n  {file_path.name} \n  -> {new_file_path.name}")
                    renamed_count += 1
                except Exception as e:
                    logger.error(f"Error renaming {file_path.name}: {str(e)}")
    
    logger.info(f"\nSummary: {renamed_count} files {'would be ' if dry_run else ''}renamed.")
    return renamed_count

def main():
    """Main function to run the Sonarr renamer"""
    parser = argparse.ArgumentParser(
        description='Rename video files to match Sonarr naming conventions'
    )
    
    # Required arguments
    parser.add_argument(
        '--input_dir', 
        required=True,
        help='Directory containing video files to rename'
    )
    
    # Optional arguments
    parser.add_argument(
        '--naming_format', 
        choices=list(SONARR_FORMATS.keys()) + ['custom'],
        default='standard',
        help='Naming format to use'
    )
    
    parser.add_argument(
        '--custom_format',
        help='Custom naming format (used if --naming_format=custom)'
    )
    
    parser.add_argument(
        '--recursive', 
        action='store_true',
        help='Process subdirectories recursively'
    )
    
    parser.add_argument(
        '--dry_run', 
        action='store_true',
        help='Show what would be renamed without actually renaming'
    )
    
    # Sonarr integration
    parser.add_argument(
        '--sonarr_url',
        help='Sonarr API URL (e.g., http://localhost:8989)'
    )
    
    parser.add_argument(
        '--api_key',
        help='Sonarr API key'
    )
    
    args = parser.parse_args()
    
    # Determine the format to use
    naming_format = args.naming_format
    if naming_format == 'custom':
        if not args.custom_format:
            logger.error("Custom format specified but --custom_format not provided")
            sys.exit(1)
        naming_format = args.custom_format
    
    # Run the renamer
    rename_for_sonarr(
        args.input_dir,
        naming_format=naming_format,
        recursive=args.recursive,
        dry_run=args.dry_run,
        sonarr_url=args.sonarr_url,
        api_key=args.api_key
    )

if __name__ == "__main__":
    main()