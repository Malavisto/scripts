import os
import subprocess
import argparse
import json
import re
from pathlib import Path

def extract_streams(video_path, output_dir, extract_audio=True, extract_signs_only=True):
    """
    Extract audio and/or subtitle streams from a video file.
    Extracts audio without transcoding and handles English subtitles marked as 'signs'.
    
    Args:
        video_path (str): Path to the video file
        output_dir (str): Directory to save extracted streams
        extract_audio (bool): Whether to extract audio
        extract_signs_only (bool): Whether to extract only signs subtitles and skip regular subs
        
    Returns:
        dict: Paths to extracted audio and subtitle files
    """
    video_name = os.path.basename(video_path)
    name_without_ext = os.path.splitext(video_name)[0]
    
    # Create a dedicated output directory for this video
    video_output_dir = os.path.join(output_dir, name_without_ext)
    os.makedirs(video_output_dir, exist_ok=True)
    
    # Initialize return dictionary
    extracted_files = {
        'audio': None,
        'signs_subtitle': None
    }
    
    # Step 1: Get stream information with more detailed tags
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 
           'stream=index,codec_name,codec_type:stream_tags=language,title,handler_name', 
           '-of', 'json', video_path]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    probe_data = json.loads(result.stdout)
    
    audio_streams = []
    subtitle_streams = []
    
    # Parse stream information
    for stream in probe_data.get('streams', []):
        index = stream.get('index')
        codec_type = stream.get('codec_type')
        codec_name = stream.get('codec_name', '')
        tags = stream.get('tags', {})
        
        language = tags.get('language', 'und').lower()
        title = tags.get('title', '').lower() if 'title' in tags else ''
        handler = tags.get('handler_name', '').lower() if 'handler_name' in tags else ''
        
        # Debug information
        print(f"Stream {index}: type={codec_type}, codec={codec_name}, lang={language}, title='{title}'")
        
        # Check for audio streams
        if codec_type == 'audio' and (language == 'eng' or language == 'und'):
            audio_streams.append({
                'index': index,
                'language': language,
                'codec_name': codec_name
            })
        
        # Check for subtitle streams - look for English signs subtitles
        elif codec_type == 'subtitle':
            is_english = language == 'eng' or language == 'en'
            # Improved detection of signs & songs subtitles
            is_signs = ('sign' in title or 'song' in title or 
                       'sign' in handler or 'song' in handler or
                       'subtitle for hearing impaired' in title.lower())
            
            if (is_english or language == 'und') and (not extract_signs_only or is_signs):
                subtitle_streams.append({
                    'index': index,
                    'language': language,
                    'title': title,
                    'handler': handler,
                    'is_signs': is_signs,
                    'codec_name': codec_name
                })
    
    # Step 2: Extract streams
    if extract_audio and audio_streams:
        # Prioritize English audio streams
        eng_streams = [s for s in audio_streams if s['language'] == 'eng']
        stream_to_extract = eng_streams[0] if eng_streams else audio_streams[0]
        
        # Use mka extension for audio files as it's well supported by mkvmerge
        audio_output = os.path.join(video_output_dir, f"{name_without_ext}_audio_eng.mka")
        
        print(f"Extracting audio from {video_name} without transcoding...")
        
        audio_cmd = [
            'ffmpeg', '-i', video_path, '-map', f'0:{stream_to_extract["index"]}',
            '-c:a', 'copy', audio_output
        ]
        
        subprocess.run(audio_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Audio saved to {audio_output}")
        extracted_files['audio'] = audio_output
        
    # Step 3: Extract subtitles (prioritizing signs)
    if extract_signs_only and subtitle_streams:
        # First prioritize English signs subtitles
        signs_streams = [s for s in subtitle_streams if s['is_signs']]
        
        if signs_streams:
            stream = signs_streams[0]
            
            # For subtitles, prefer ASS/SSA format
            subtitle_output = os.path.join(
                video_output_dir, 
                f"{name_without_ext}_subs_signs.{stream['codec_name']}"
            )
            
            print(f"Extracting Signs & Songs subtitles from {video_name}...")
            
            subs_cmd = [
                'ffmpeg', '-i', video_path, '-map', f'0:{stream["index"]}',
                '-c:s', 'copy', subtitle_output
            ]
            
            subprocess.run(subs_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Signs subtitles saved to {subtitle_output}")
            
            extracted_files['signs_subtitle'] = subtitle_output
        else:
            print("No Signs & Songs subtitles found.")
    
    return extracted_files

def find_matching_sub_file(dub_file, sub_dir):
    """
    Find the matching subtitle version file in the SUB directory
    
    Args:
        dub_file (str): Path to the DUB file
        sub_dir (str): Path to the SUB directory
        
    Returns:
        str: Path to the matching SUB file, or None if not found
    """
    dub_filename = os.path.basename(dub_file)
    
    # Extract episode information using regex
    match = re.search(r'(S\d+E\d+)', dub_filename, re.IGNORECASE)
    if not match:
        print(f"Could not extract episode information from {dub_filename}")
        return None
    
    episode_code = match.group(1)
    
    # Find matching file in SUB directory
    for sub_file in os.listdir(sub_dir):
        if episode_code in sub_file.upper():  # Case-insensitive comparison
            return os.path.join(sub_dir, sub_file)
    
    print(f"No matching SUB file found for episode {episode_code}")
    return None

def merge_with_mkvmerge(sub_video_path, audio_path, signs_subtitle_path, output_path):
    """
    Merge streams using mkvmerge instead of ffmpeg
    
    Args:
        sub_video_path (str): Path to the SUB video file
        audio_path (str): Path to the extracted audio file
        signs_subtitle_path (str): Path to the extracted signs subtitle file
        output_path (str): Path to save the merged file
        
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"Merging streams for {os.path.basename(sub_video_path)} using mkvmerge...")
    
    # Start with the base command
    cmd = ['mkvmerge', '-o', output_path, sub_video_path]
    
    # Add audio if available
    if audio_path:
        cmd.extend([audio_path])
    
    # Add signs subtitles if available
    if signs_subtitle_path:
        cmd.extend([
            '--track-name', '0:Track 2 - Signs & Songs',
            '--language', '0:eng',
            signs_subtitle_path
        ])
    
    print("Running command:", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Successfully merged streams to {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error merging streams: {e}")
        print(f"STDERR: {e.stderr.decode()}")
        return False
    except FileNotFoundError:
        print("mkvmerge command not found. Make sure MKVToolNix is installed.")
        return False

def process_dub_sub_folders(dub_dir, sub_dir, output_dir, temp_dir=None):
    """
    Process all matching video files in DUB and SUB directories
    
    Args:
        dub_dir (str): Directory containing DUB video files
        sub_dir (str): Directory containing SUB video files
        output_dir (str): Directory to save merged videos
        temp_dir (str, optional): Directory to save temporary extracted streams
    """
    if temp_dir is None:
        temp_dir = os.path.join(output_dir, "extracted_streams")
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    # Video file extensions to look for
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    
    for filename in os.listdir(dub_dir):
        file_path = os.path.join(dub_dir, filename)
        
        # Skip if not a video file
        if not os.path.isfile(file_path) or not any(filename.lower().endswith(ext) for ext in video_extensions):
            continue
        
        try:
            # Step 1: Find matching SUB file
            sub_file_path = find_matching_sub_file(file_path, sub_dir)
            if not sub_file_path:
                print(f"Skipping {filename} - no matching SUB file found")
                continue
            
            # Step 2: Extract audio and signs subtitles from DUB file
            extracted = extract_streams(file_path, temp_dir, extract_audio=True, extract_signs_only=True)
            
            # Step 3: Prepare output path - adding "_Dual" to indicate dual audio
            output_base = os.path.splitext(os.path.basename(sub_file_path))[0]
            output_filename = f"{output_base}_Dual.mkv"
            output_path = os.path.join(output_dir, output_filename)
            
            # Step 4: Merge streams using mkvmerge
            merge_with_mkvmerge(
                sub_file_path,
                extracted['audio'],
                extracted['signs_subtitle'],
                output_path
            )
            
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            import traceback
            traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description='Extract audio/signs subtitles from DUB videos and merge with SUB videos using mkvmerge')
    parser.add_argument('--dub_dir', help='Directory containing DUB videos', default='./DUB')
    parser.add_argument('--sub_dir', help='Directory containing SUB videos', default='./SUB')
    parser.add_argument('--output_dir', help='Directory to save merged videos', default='./Merged')
    parser.add_argument('--temp_dir', help='Directory to save temporary extracted streams', default=None)
    parser.add_argument('--single', help='Process only a single DUB file (specify full path)')
    parser.add_argument('--single_sub', help='Process with a specific SUB file (specify full path, requires --single)')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Set up temp directory
    if args.temp_dir is None:
        args.temp_dir = os.path.join(args.output_dir, "extracted_streams")
    os.makedirs(args.temp_dir, exist_ok=True)
    
    # Process a single file if specified
    if args.single:
        if not os.path.isfile(args.single):
            print(f"Error: {args.single} is not a valid file")
            return
        
        dub_file = args.single
        
        # Find matching SUB file or use the one specified
        if args.single_sub:
            if not os.path.isfile(args.single_sub):
                print(f"Error: {args.single_sub} is not a valid file")
                return
            sub_file = args.single_sub
        else:
            sub_file = find_matching_sub_file(dub_file, args.sub_dir)
            if not sub_file:
                print(f"No matching SUB file found for {os.path.basename(dub_file)}")
                return
        
        # Extract and merge
        extracted = extract_streams(dub_file, args.temp_dir, extract_audio=True, extract_signs_only=True)
        output_base = os.path.splitext(os.path.basename(sub_file))[0]
        output_path = os.path.join(args.output_dir, f"{output_base}_Dual.mkv")
        
        merge_with_mkvmerge(
            sub_file,
            extracted['audio'],
            extracted['signs_subtitle'],
            output_path
        )
    else:
        # Process all files in the directories
        process_dub_sub_folders(args.dub_dir, args.sub_dir, args.output_dir, args.temp_dir)

if __name__ == "__main__":
    main()
