import os
import subprocess
import argparse
import json
from pathlib import Path

def extract_streams(video_path, output_dir, extract_audio=True, extract_subs=True):
    """
    Extract audio and/or subtitle streams from a video file.
    Extracts audio without transcoding and handles English subtitles including those marked as 'signs'.
    
    Args:
        video_path (str): Path to the video file
        output_dir (str): Directory to save extracted streams
        extract_audio (bool): Whether to extract audio
        extract_subs (bool): Whether to extract subtitles
    """
    video_name = os.path.basename(video_path)
    name_without_ext = os.path.splitext(video_name)[0]
    
    # Create a dedicated output directory for this video
    video_output_dir = os.path.join(output_dir, name_without_ext)
    os.makedirs(video_output_dir, exist_ok=True)
    
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
        
        # Check for audio streams
        if codec_type == 'audio' and (language == 'eng' or language == 'und'):
            audio_streams.append({
                'index': index,
                'language': language,
                'codec_name': codec_name
            })
        
        # Check for subtitle streams - look for English or signs subtitles
        elif codec_type == 'subtitle':
            is_english = language == 'eng' or language == 'en'
            is_signs = 'sign' in title or 'sign' in handler
            
            if is_english or is_signs or language == 'und':
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
        
        # Use original extension if possible, otherwise default to m4a which works with most codecs
        ext = 'mka' if stream_to_extract['codec_name'] in ['aac', 'ac3', 'eac3', 'dts', 'truehd'] else 'm4a'
        audio_output = os.path.join(video_output_dir, f"{name_without_ext}_audio_eng.{ext}")
        
        print(f"Extracting audio from {video_name} without transcoding...")
        
        audio_cmd = [
            'ffmpeg', '-i', video_path, '-map', f'0:{stream_to_extract["index"]}',
            '-c:a', 'copy', audio_output
        ]
        
        subprocess.run(audio_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Audio saved to {audio_output}")
        
    if extract_subs and subtitle_streams:
        # First prioritize English signs subtitles, then regular English, then undefined
        signs_streams = [s for s in subtitle_streams if s['is_signs']]
        eng_streams = [s for s in subtitle_streams if s['language'] == 'eng' and not s['is_signs']]
        
        streams_to_extract = []
        
        # Add signs subtitles if they exist
        if signs_streams:
            streams_to_extract.append(signs_streams[0])
        
        # Also add regular English subtitles if they exist and are different from signs
        if eng_streams and not signs_streams:
            streams_to_extract.append(eng_streams[0])
        
        # If no English subtitles found, use undefined language
        if not streams_to_extract:
            und_streams = [s for s in subtitle_streams if s['language'] == 'und']
            if und_streams:
                streams_to_extract.append(und_streams[0])
        
        # Extract each subtitle stream
        for stream in streams_to_extract:
            # Determine a descriptive suffix based on subtitle type
            suffix = "_signs" if stream['is_signs'] else "_eng"
            
            # Preserve the original subtitle format
            subtitle_output = os.path.join(
                video_output_dir, 
                f"{name_without_ext}_subs{suffix}.{stream['codec_name']}"
            )
            
            print(f"Extracting subtitles ({suffix.strip('_')}) from {video_name}...")
            
            subs_cmd = [
                'ffmpeg', '-i', video_path, '-map', f'0:{stream["index"]}',
                '-c:s', 'copy', subtitle_output
            ]
            
            subprocess.run(subs_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Subtitles saved to {subtitle_output}")

def process_folder(input_folder, output_folder, extract_audio=True, extract_subs=True):
    """
    Process all video files in a folder to extract English audio and subtitles.
    
    Args:
        input_folder (str): Folder containing video files
        output_folder (str): Folder to save extracted streams
        extract_audio (bool): Whether to extract audio
        extract_subs (bool): Whether to extract subtitles
    """
    # Video file extensions to look for
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    
    for filename in os.listdir(input_folder):
        file_path = os.path.join(input_folder, filename)
        
        # Check if it's a file and has a video extension
        if os.path.isfile(file_path) and any(filename.lower().endswith(ext) for ext in video_extensions):
            try:
                extract_streams(file_path, output_folder, extract_audio, extract_subs)
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract audio and subtitles from video files')
    parser.add_argument('input_folder', help='Folder containing video files')
    parser.add_argument('--output_folder', help='Folder to save extracted streams (default: ./extracted)', default='./extracted')
    parser.add_argument('--audio_only', action='store_true', help='Extract only audio')
    parser.add_argument('--subs_only', action='store_true', help='Extract only subtitles')
    
    args = parser.parse_args()
    
    extract_audio = not args.subs_only
    extract_subs = not args.audio_only
    
    process_folder(args.input_folder, args.output_folder, extract_audio, extract_subs)
