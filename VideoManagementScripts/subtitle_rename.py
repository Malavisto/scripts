#!/usr/bin/env python3
import os
import argparse
import re
from pathlib import Path

def is_subtitle_file(filename):
    """Check if a file is a subtitle file based on its extension."""
    subtitle_extensions = ['.srt', '.ass', '.ssa', '.sub', '.idx', '.vtt', '.smi']
    return any(filename.lower().endswith(ext) for ext in subtitle_extensions)

def rename_subtitles(base_dir, dry_run=False, rename_pattern="signs", verbose=False):
    """
    Scan directories and rename subtitle files according to a consistent pattern.
    
    Args:
        base_dir (str): Base directory to scan for subtitle files
        dry_run (bool): If True, show what would be renamed without actually renaming
        rename_pattern (str): Type of subtitle to mark files as (signs, eng, etc.)
        verbose (bool): If True, show more detailed output
    """
    renamed_count = 0
    scanned_count = 0
    
    # Walk through all subdirectories
    for root, dirs, files in os.walk(base_dir):
        # Get the parent folder name which should be the video name
        parent_folder = os.path.basename(root)
        
        subtitle_files = [f for f in files if is_subtitle_file(f)]
        
        if verbose and subtitle_files:
            print(f"\nProcessing directory: {root}")
            
        for filename in subtitle_files:
            scanned_count += 1
            file_path = os.path.join(root, filename)
            file_base, file_ext = os.path.splitext(filename)
            
            # Check if the file already follows our naming pattern (has _signs or _eng in the name)
            if "_signs" in file_base.lower() or "_eng" in file_base.lower():
                if verbose:
                    print(f"  Skipping (already named properly): {filename}")
                continue
                
            # Construct new filename
            if parent_folder and parent_folder != '.':
                # Use the parent folder name as the base name
                new_name = f"{parent_folder}_subs_{rename_pattern}{file_ext}"
            else:
                # If we're not in a proper subdirectory, just add the suffix to the original name
                new_name = f"{file_base}_subs_{rename_pattern}{file_ext}"
                
            new_path = os.path.join(root, new_name)
            
            # Check if the target file already exists
            if os.path.exists(new_path):
                print(f"  Skipping (target exists): {filename} → {new_name}")
                continue
                
            if dry_run:
                print(f"  Would rename: {filename} → {new_name}")
            else:
                try:
                    os.rename(file_path, new_path)
                    print(f"  Renamed: {filename} → {new_name}")
                    renamed_count += 1
                except Exception as e:
                    print(f"  Error renaming {filename}: {str(e)}")
    
    # Print summary
    action = "Would rename" if dry_run else "Renamed"
    print(f"\nSummary: Scanned {scanned_count} subtitle files. {action} {renamed_count} files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk rename subtitle files to a consistent format")
    parser.add_argument("directory", help="Directory to scan for subtitle files")
    parser.add_argument("--pattern", default="signs", help="Subtitle type pattern (default: signs)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be renamed without making changes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show more detailed output")
    
    args = parser.parse_args()
    
    # Validate the directory
    if not os.path.isdir(args.directory):
        print(f"Error: {args.directory} is not a valid directory")
        exit(1)
        
    print(f"Scanning for subtitle files in: {args.directory}")
    if args.dry_run:
        print("Running in dry-run mode. No files will be renamed.")
        
    rename_subtitles(args.directory, args.dry_run, args.pattern, args.verbose)