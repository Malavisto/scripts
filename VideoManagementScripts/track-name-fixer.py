#!/usr/bin/env python3
"""
MKV Track Name Fixer

This script standardizes track names in MKV files created by the video-extract-merge.py script.
It ensures consistent naming conventions across audio and subtitle tracks.

Usage:
    python track-name-fixer.py [--input_dir DIRECTORY] [--single FILE]
"""

import os
import sys
import subprocess
import argparse
import json
import re
import shlex
from pathlib import Path

def get_track_info(mkv_file):
    """
    Get detailed track information from an MKV file using mkvmerge.
    
    Args:
        mkv_file (str): Path to the MKV file
        
    Returns:
        list: List of track objects with details
    """
    try:
        # Use raw file path to avoid escape character issues
        # Convert to Path object and then to string to handle paths properly
        mkv_path = Path(mkv_file).resolve()
        cmd = ['mkvmerge', '-J', str(mkv_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)
        
        # Debug: Print the full track info
        # print(json.dumps(info.get('tracks', []), indent=2))
        
        return info.get('tracks', [])
    except subprocess.CalledProcessError as e:
        print(f"Error analyzing {mkv_file}: {e}")
        print(f"STDERR: {e.stderr}")
        return []
    except json.JSONDecodeError:
        print(f"Error parsing mkvmerge output for {mkv_file}")
        return []
    except FileNotFoundError:
        print("mkvmerge command not found. Make sure MKVToolNix is installed.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error processing {mkv_file}: {str(e)}")
        return []

def get_track_spec(track):
    """
    Convert track information to the correct mkvpropedit track specification.
    
    mkvpropedit tracks are specified simply by their ID number (starting from 1)
    as they appear in MKVToolNixGUI and mkvinfo.
    
    Args:
        track (dict): Track information from mkvmerge
        
    Returns:
        str: Track specification for mkvpropedit
    """
    # Get the track number (most accurate for mkvpropedit)
    # Add 1 because mkvpropedit track numbers are 1-based
    track_id = track.get('id', 0) + 1
    
    # Return the track ID directly as a string
    track_spec = f"{track_id}"
    return track_spec

def fix_track_names(mkv_file, dry_run=False, debug=False):
    """
    Fix track names in an MKV file to use a consistent naming scheme.
    
    Args:
        mkv_file (str): Path to the MKV file
        dry_run (bool): If True, only print the commands without executing them
        debug (bool): If True, print additional debug information
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Ensure we're working with a proper path object
    mkv_path = Path(mkv_file).resolve()
    
    if not mkv_path.exists():
        print(f"Error: File {mkv_path} does not exist")
        return False
    
    print(f"\nProcessing: {mkv_path.name}")
    
    # Check if the file is accessible
    if not os.access(mkv_path, os.R_OK | os.W_OK):
        print(f"Error: No read/write permission for {mkv_path}")
        return False
        
    tracks = get_track_info(str(mkv_path))
    if not tracks:
        print(f"No tracks found in {mkv_path}")
        return False
    
    if debug:
        print("Track details from mkvmerge:")
        for track in tracks:
            print(f"  ID: {track.get('id')}, Type: {track.get('type')}, Properties: {track.get('properties')}")
    
    # Track naming templates
    naming_scheme = {
        'video': {
            'name': 'Main Video',
            'language': 'und'  # Usually video doesn't need language tag
        },
        'audio': {
            'jpn': {'name': 'Japanese Audio', 'language': 'jpn'},
            'eng': {'name': 'English Audio', 'language': 'eng'},
            'und': {'name': 'Audio', 'language': 'und'}
        },
        'subtitles': {
            'eng_signs': {'name': 'Signs & Songs', 'language': 'eng', 'forced': True},
            'eng': {'name': 'English', 'language': 'eng', 'forced': False},
            'jpn': {'name': 'Japanese', 'language': 'jpn', 'forced': False},
            'und': {'name': 'Subtitles', 'language': 'und', 'forced': False}
        }
    }
    
    commands = []
    
    for track in tracks:
        track_type = track.get('type', '')
        properties = track.get('properties', {})
        
        # Get the correct track specification for mkvpropedit
        track_spec = get_track_spec(track)
        if not track_spec:
            print(f"  Skipping track {track.get('id', 0)}: Unknown type '{track_type}'")
            continue
            
        current_lang = properties.get('language', 'und').lower()
        current_name = properties.get('track_name', '')
        current_forced = properties.get('forced_track', False)
        
        # Determine the appropriate name and settings based on track type and properties
        new_name = None
        new_lang = None
        new_forced = None
        
        # Print current information
        print(f"  Track {track_spec}: {track_type}, current name: '{current_name}', lang: {current_lang}, forced: {current_forced}")
        
        if track_type == 'video':
            new_name = naming_scheme['video']['name']
            new_lang = naming_scheme['video']['language']
            
        elif track_type == 'audio':
            # Check if this is Japanese or English audio
            is_japanese = current_lang == 'jpn' or 'japan' in current_name.lower()
            is_english = current_lang == 'eng' or 'english' in current_name.lower()
            
            if is_japanese:
                new_name = naming_scheme['audio']['jpn']['name']
                new_lang = 'jpn'
            elif is_english or current_lang == 'eng':
                new_name = naming_scheme['audio']['eng']['name']
                new_lang = 'eng'
            else:
                new_name = naming_scheme['audio']['und']['name']
                new_lang = current_lang
                
        elif track_type == 'subtitles':
            # Check if this is a signs & songs track
            is_signs = ('sign' in current_name.lower() or 
                       'song' in current_name.lower() or 
                       'subtitle for hearing impaired' in current_name.lower() or
                       '2 -' in current_name.lower())  # Detect "Track 2 - Signs & Songs"
            
            is_english = current_lang == 'eng' or 'english' in current_name.lower()
            is_japanese = current_lang == 'jpn' or 'japan' in current_name.lower()
            
            if is_english and is_signs:
                new_name = naming_scheme['subtitles']['eng_signs']['name']
                new_lang = 'eng'
                new_forced = naming_scheme['subtitles']['eng_signs']['forced']
            elif is_english:
                new_name = naming_scheme['subtitles']['eng']['name']
                new_lang = 'eng'
                new_forced = naming_scheme['subtitles']['eng']['forced']
            elif is_japanese:
                new_name = naming_scheme['subtitles']['jpn']['name']
                new_lang = 'jpn'
                new_forced = naming_scheme['subtitles']['jpn']['forced']
            else:
                new_name = naming_scheme['subtitles']['und']['name']
                new_lang = current_lang
                new_forced = naming_scheme['subtitles']['und']['forced']
        
        # Only add commands if we need to change something
        track_changes_needed = False
        track_cmd = ['mkvpropedit', mkv_file, '--edit', 'track:' + track_spec]
            
        if new_name and new_name != current_name:
            track_cmd.extend(['--set', f'name={new_name}'])
            print(f"  → Renaming to: '{new_name}'")
            track_changes_needed = True
        
        if new_lang and new_lang != current_lang:
            track_cmd.extend(['--set', f'language={new_lang}'])
            print(f"  → Setting language to: {new_lang}")
            track_changes_needed = True
            
        if new_forced is not None and new_forced != current_forced:
            # Convert boolean to string representation for mkvpropedit
            forced_value = '1' if new_forced else '0'
            track_cmd.extend(['--set', f'flag-forced={forced_value}'])
            print(f"  → Setting forced flag to: {new_forced}")
            track_changes_needed = True
                
        if track_changes_needed:
            commands.append(track_cmd)
    
    # Execute the commands
    if commands:
        if dry_run:
            print("\nCommands that would be executed:")
            for cmd in commands:
                cmd_str = " ".join(shlex.quote(str(part)) for part in cmd)
                print(cmd_str)
            return True
        else:
            success = True
            for cmd in commands:
                try:
                    # Use shlex.quote to properly display the command with escaping
                    cmd_str = " ".join(shlex.quote(str(part)) for part in cmd)
                    print(f"Executing: {cmd_str}")
                    
                    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                    if debug and result.stdout:
                        print(f"  STDOUT: {result.stdout}")
                except subprocess.CalledProcessError as e:
                    print(f"Error: Command returned non-zero exit status {e.returncode}")
                    print(f"STDERR: {e.stderr}")
                    success = False
                except Exception as e:
                    print(f"Unexpected error executing command: {str(e)}")
                    success = False
            
            if success:
                print(f"Successfully updated track properties in {mkv_path.name}")
            return success
    else:
        print("No track property changes needed.")
        return True

def process_directory(input_dir, dry_run=False, debug=False):
    """
    Process all MKV files in a directory to fix track names.
    
    Args:
        input_dir (str): Directory containing MKV files
        dry_run (bool): If True, only print the commands without executing them
        debug (bool): If True, print additional debug information
    """
    input_path = Path(input_dir).resolve()
    
    if not input_path.is_dir():
        print(f"Error: {input_path} is not a valid directory")
        return
    
    # Find all MKV files in the directory using pathlib
    mkv_files = list(input_path.glob('*.mkv'))
    
    if not mkv_files:
        print(f"No MKV files found in {input_path}")
        return
    
    print(f"Found {len(mkv_files)} MKV files in {input_path}")
    
    success_count = 0
    for mkv_file in mkv_files:
        if fix_track_names(mkv_file, dry_run, debug):
            success_count += 1
    
    print(f"\nProcessed {len(mkv_files)} files, {success_count} successfully updated")

def main():
    parser = argparse.ArgumentParser(description='Fix track naming schemes in MKV files')
    parser.add_argument('--input_dir', help='Directory containing MKV files to process', default='./Merged')
    parser.add_argument('--single', help='Process only a single MKV file (specify full path)')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying them')
    parser.add_argument('--debug', action='store_true', help='Print additional debug information')
    
    args = parser.parse_args()
    
    if args.single:
        single_path = Path(args.single).resolve()
        if not single_path.is_file():
            print(f"Error: {single_path} is not a valid file")
            return
        fix_track_names(single_path, args.dry_run, args.debug)
    else:
        process_directory(args.input_dir, args.dry_run, args.debug)

if __name__ == "__main__":
    main()
