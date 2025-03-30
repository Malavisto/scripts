import os
import re
import argparse
import subprocess
from pathlib import Path

def get_video_codec(file_path):
    """
    Get the video codec information using ffprobe
    """
    try:
        cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', 
               '-show_entries', 'stream=codec_name', '-of', 'default=noprint_wrappers=1:nokey=1', 
               file_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        codec = result.stdout.strip()
        
        # Map common codec names to more readable versions
        codec_map = {
            'h264': 'H264',
            'hevc': 'HEVC',
            'av1': 'AV1',
            'mpeg4': 'MPEG4',
            'vp9': 'VP9',
            'vp8': 'VP8'
        }
        
        return codec_map.get(codec.lower(), codec.upper())
    except Exception as e:
        print(f"Error getting codec info: {e}")
        return "UNKNOWN"

def extract_episode_info(filename):
    """
    Extract show name, season number, and episode number from filename
    """
    # Remove file extension
    name_without_ext = os.path.splitext(filename)[0]
    
    # Various regex patterns to match different episode naming conventions
    
    # Pattern 1: ShowName.S01E02 or ShowName.1x02
    pattern1 = re.compile(r'(.+?)[.\s_-]*(?:s|season)?(\d{1,2})(?:e|x|episode)(\d{1,2})', re.IGNORECASE)
    
    # Pattern 2: ShowName.102 (season 1 episode 02)
    pattern2 = re.compile(r'(.+?)[.\s_-]*(\d)(\d{2})\b', re.IGNORECASE)
    
    # Pattern 3: ShowName - 102 (Season 1 Episode 02)
    pattern3 = re.compile(r'(.+?)[.\s_-]+(?:\[?(?:episode|ep)[.\s_-]*)?(\d{1,2})(?:[.\s_-]*of[.\s_-]*\d{1,2})?(?:\])?', re.IGNORECASE)
    
    # Try each pattern in order
    match = pattern1.search(name_without_ext)
    if match:
        show_name = match.group(1).replace('.', ' ').strip()
        season_num = int(match.group(2))
        episode_num = int(match.group(3))
        return clean_show_name(show_name), season_num, episode_num
    
    match = pattern2.search(name_without_ext)
    if match:
        show_name = match.group(1).replace('.', ' ').strip()
        season_num = int(match.group(2))
        episode_num = int(match.group(3))
        return clean_show_name(show_name), season_num, episode_num
    
    match = pattern3.search(name_without_ext)
    if match:
        show_name = match.group(1).replace('.', ' ').strip()
        # Assume season 1 if only episode number is present
        return clean_show_name(show_name), 1, int(match.group(2))
    
    # If no pattern matches, return defaults
    return clean_show_name(name_without_ext), 1, 1

def clean_show_name(name):
    """Clean up show name by removing common unwanted elements"""
    # Remove common tags like [1080p], (HEVC), etc.
    name = re.sub(r'\[.*?\]|\(.*?\)|\{.*?\}', '', name)
    
    # Remove other common elements
    remove_list = [
        'bdrip', 'bluray', 'dvdrip', 'webdl', 'webrip', 'hdtv', 
        '1080p', '720p', '480p', '2160p', '4k', 'x264', 'x265',
        'aac', 'ac3', 'mp3', 'flac', 'subtitled', 'subbed', 'dubbed'
    ]
    
    pattern = '|'.join(rf'\b{re.escape(x)}\b' for x in remove_list)
    name = re.sub(pattern, '', name, flags=re.IGNORECASE)
    
    # Clean up multiple spaces and trailing/leading spaces
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Remove trailing hyphen or underscore and clean up again
    name = re.sub(r'[-_]+$', '', name).strip()
    
    return name

def rename_episodes(folder_path, dry_run=False, recursive=False):
    """
    Rename episode files with a consistent format: ShowName_SxxExx_CODEC.ext
    """
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' not found.")
        return
    
    # Video file extensions
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    
    # Collect all files to process
    files_to_process = []
    
    if recursive:
        for root, _, files in os.walk(folder_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    files_to_process.append((root, file))
    else:
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            if os.path.isfile(file_path) and any(file.lower().endswith(ext) for ext in video_extensions):
                files_to_process.append((folder_path, file))
    
    renamed_count = 0
    
    # Process all files
    for folder, filename in files_to_process:
        full_path = os.path.join(folder, filename)
        
        # Get file information
        show_name, season_num, episode_num = extract_episode_info(filename)
        codec = get_video_codec(full_path)
        _, extension = os.path.splitext(filename)
        
        # Create new filename
        new_filename = f"{show_name}_S{season_num:02d}E{episode_num:02d}_{codec}{extension.lower()}"
        # Replace spaces with underscores in final name
        new_filename = new_filename.replace(' ', '_')
        # Remove any other problematic characters
        new_filename = re.sub(r'[^\w\-\.]', '', new_filename)
        
        new_full_path = os.path.join(folder, new_filename)
        
        # Handle name conflicts
        counter = 1
        base_new_filename = new_filename
        while os.path.exists(new_full_path) and new_full_path != full_path and not dry_run:
            base_name, extension = os.path.splitext(base_new_filename)
            new_filename = f"{base_name}_{counter}{extension}"
            new_full_path = os.path.join(folder, new_filename)
            counter += 1
        
        if dry_run:
            print(f"Would rename: \n  {filename} \n  -> {new_filename}")
        else:
            if new_full_path != full_path:
                try:
                    os.rename(full_path, new_full_path)
                    print(f"Renamed: \n  {filename} \n  -> {new_filename}")
                    renamed_count += 1
                except Exception as e:
                    print(f"Error renaming {filename}: {e}")
    
    print(f"\nSummary: {renamed_count} files {'would be ' if dry_run else ''}renamed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Rename episode files with a consistent format')
    parser.add_argument('folder', help='Folder containing episode files to rename')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be renamed without actually renaming')
    parser.add_argument('--recursive', action='store_true', help='Process subfolders recursively')
    
    args = parser.parse_args()
    
    rename_episodes(args.folder, args.dry_run, args.recursive)