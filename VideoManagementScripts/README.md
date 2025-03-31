# Video Management Scripts

A collection of Python scripts for managing, processing, and organizing video files and related media.

## Overview

This repository contains various utility scripts for managing video files, including renaming episodes, merging media elements (video, audio, subtitles), organizing files, and processing subtitles.

## Requirements

- Python 3.6+
- FFmpeg (required for most scripts)
- ffprobe (component of FFmpeg, used for media analysis)
- MKVToolNix (required for MKV manipulation scripts)

## Scripts

### 1. auto-video-processor.py (Main Script)

The primary script that automates the entire video processing workflow by utilizing the other scripts in this collection.

#### Features:
- Coordinates the complete video processing pipeline in a single command
- Handles file renaming, audio/subtitle extraction, merging, and track name standardization
- Provides detailed logging of all operations
- Supports dry-run mode to preview actions without changing files
- Configurable to skip specific processing steps as needed

#### Usage:
```bash
python auto-video-processor.py [--video_dir VIDEO_DIR] [--extract_dir EXTRACT_DIR] 
                              [--output_dir OUTPUT_DIR] [--dry_run] [--recursive]
                              [--skip_rename] [--skip_extract]
```

#### Example:

Process videos using default directories (./Video, ./Extracted, ./Merged):
```bash
python auto-video-processor.py
```

Process videos in a specific directory with custom output locations:
```bash
python auto-video-processor.py --video_dir /path/to/videos --extract_dir ./extracted_content --output_dir ./processed
```

Preview all operations without making changes:
```bash
python auto-video-processor.py --dry_run
```

Skip the renaming step and only process extraction and merging:
```bash
python auto-video-processor.py --skip_rename
```

### 2. auto-video-processor-sonarr.py

An extended version of the auto-video-processor script that adds Sonarr-compatible file renaming as the final step in the workflow.

#### Features:
- Includes all functionality from auto-video-processor.py
- Adds automatic renaming of output files to match Sonarr naming conventions
- Optionally retrieves episode titles from Sonarr API
- Supports multiple Sonarr naming formats
- Can be configured to skip any step in the process

#### Usage:
```bash
python auto-video-processor-sonarr.py [--video_dir VIDEO_DIR] [--extract_dir EXTRACT_DIR] 
                                     [--output_dir OUTPUT_DIR] [--dry_run] [--recursive]
                                     [--skip_rename] [--skip_extract] [--sonarr_format FORMAT]
                                     [--sonarr_url URL] [--api_key KEY] [--skip_sonarr_rename]
```

#### Example:

Process videos and rename according to Sonarr conventions:
```bash
python auto-video-processor-sonarr.py --sonarr_format standard_episode
```

Process videos and rename with Sonarr integration to get episode titles:
```bash
python auto-video-processor-sonarr.py --sonarr_format standard_episode --sonarr_url http://localhost:8989 --api_key YOUR_API_KEY
```

Process videos using a custom naming format:
```bash
python auto-video-processor-sonarr.py --sonarr_format custom --custom_format "{Series Title} - {season}x{episode:02d}"
```

### 3. sonarr-renamer.py

A standalone script that renames video files to match Sonarr's naming conventions, ideal for post-processing after using auto-video-processor.py.

#### Features:
- Multiple built-in naming formats to match different Sonarr preferences
- Optional integration with Sonarr API to fetch episode titles
- Preserves video codec information in filenames
- Supports recursive directory processing
- Dry-run mode to preview changes
- Detailed logging

#### Usage:
```bash
python sonarr-renamer.py --input_dir INPUT_DIR [--naming_format FORMAT]
                         [--dry_run] [--recursive] [--api_key API_KEY] 
                         [--sonarr_url SONARR_URL]
```

#### Supported Naming Formats:
- `standard`: "Show Name - S01E05"
- `standard_episode`: "Show Name - S01E05 - Episode Title"
- `scene`: "Show.Name.S01E05"
- `scene_episode`: "Show.Name.S01E05.Episode.Title"
- `folder_season_episode`: "Show Name/Season 1/S01E05 - Episode Title"
- `custom`: Custom format defined with `--custom_format`

#### Example:

Rename all video files in a directory to standard Sonarr format:
```bash
python sonarr-renamer.py --input_dir ./Merged --naming_format standard
```

Rename video files with episode titles from Sonarr:
```bash
python sonarr-renamer.py --input_dir ./Merged --naming_format standard_episode --sonarr_url http://localhost:8989 --api_key YOUR_API_KEY
```

Preview renaming using the scene format:
```bash
python sonarr-renamer.py --input_dir ./Merged --naming_format scene --dry_run
```

Create a season folder structure with episode titles:
```bash
python sonarr-renamer.py --input_dir ./Merged --naming_format folder_season_episode
```

### 4. file-renamer.py

Renames video files to follow a consistent naming convention based on show name, season, episode, and video codec.

#### Features:
- Automatically extracts show name, season, and episode information from filenames
- Adds video codec information (H264, HEVC, etc.)
- Supports dry-run mode to preview changes
- Recursive mode for processing nested directories

#### Usage:
```bash
python file-renamer.py /path/to/videos [--dry-run] [--recursive]
```
#### Example:

Preview renaming without actually changing files:
```bash
python file-renamer.py /path/to/show/files --dry-run
```

Rename all video files in directory and subdirectories:
```bash
python file-renamer.py /path/to/show/files --recursive
```

### 5. remove_pgs_subs.py

Removes PGS subtitle tracks from MKV files. Useful for removing bitmap subtitles while keeping text-based ones.

#### Features:
- Identifies and removes PGS (bitmap) subtitle tracks
- Can replace original files or save to a new location
- Preserves all other streams (video, audio, text subtitles)
- Supports dry-run mode

#### Usage:
```bash
python remove_pgs_subs.py DIRECTORY [--output-dir OUTPUT_DIR] [--dry-run]
```
#### Example:

Preview removal of PGS subtitles:
```bash
python remove_pgs_subs.py /path/to/videos --dry-run
```

Remove PGS subtitles and save to a different directory:
```bash
python remove_pgs_subs.py /path/to/videos --output-dir /path/to/output
```

### 6. subtitle_rename.py

Renames subtitle files to follow a consistent naming pattern based on their parent directory name.

#### Features:
- Standardizes subtitle filenames
- Adds suffix to indicate subtitle type (signs, eng, etc.)
- Supports dry-run mode
- Verbose output option

#### Usage:
```bash
python subtitle_rename.py DIRECTORY [--dry-run] [--pattern PATTERN] [--verbose]
```
#### Example:

Rename subtitle files with "signs" pattern:
```bash
python subtitle_rename.py /path/to/subtitles --pattern signs
```

Preview renaming with verbose output:
```bash
python subtitle_rename.py /path/to/subtitles --dry-run --verbose
```

### 7. video-extract.py

Extracts audio and subtitle streams from video files without transcoding, focusing on English audio and subtitles.

#### Features:
- Extracts audio streams preserving the original codec (no transcoding)
- Intelligently extracts English subtitles and "signs & songs" subtitles
- Creates a separate folder for each video's extracted content
- Supports batch processing of all video files in a directory
- Selective extraction of either audio, subtitles, or both

#### Usage:
```bash
python video-extract.py INPUT_FOLDER [--output_folder OUTPUT_FOLDER] [--audio_only] [--subs_only]
```
#### Example:

Extract both audio and subtitles from all videos in a folder:
```bash
python video-extract.py /path/to/videos --output_folder ./extracted_content
```

Extract only audio streams:
```bash
python video-extract.py /path/to/videos --audio_only
```

Extract only subtitle streams:
```bash
python video-extract.py /path/to/videos --subs_only
```

### 8. video-extract-merge.py

Creates new MKV files by merging original video with extracted or modified audio and subtitle tracks.

#### Features:
- Combines video tracks with separate audio and subtitle files
- Preserves original video quality (no re-encoding)
- Supports batch processing of multiple video files
- Output files maintain the original video quality with the added/modified tracks

#### Usage:
```bash
python video-extract-merge.py [--video_dir VIDEO_DIR] [--extract_dir EXTRACT_DIR] [--output_dir OUTPUT_DIR]
```

#### Example:

Merge video with extracted audio and subtitle tracks:
```bash
python video-extract-merge.py --video_dir /path/to/videos --extract_dir ./extracted_content --output_dir ./Merged
```

Use default directories (Video, Extracted, Merged):
```bash
python video-extract-merge.py
```

### 9. track-name-fixer.py

Standardizes track names in MKV files to ensure consistent naming conventions across audio and subtitle tracks.

#### Features:
- Automatically detects track types and languages
- Standardizes track names (e.g., "English Audio", "Signs & Songs")
- Sets appropriate language tags for all tracks
- Properly marks forced subtitle tracks
- Supports dry-run mode to preview changes
- Can process entire directories of MKV files or single files

#### Usage:
```bash
python track-name-fixer.py [--input_dir DIRECTORY] [--single FILE] [--dry-run] [--debug]
```

#### Example:

Fix track names in all MKV files in the default directory (./Merged):
```bash
python track-name-fixer.py
```

Process a single MKV file:
```bash
python track-name-fixer.py --single /path/to/video.mkv
```

Preview changes without applying them:
```bash
python track-name-fixer.py --input_dir /path/to/mkv/files --dry-run
```

Show detailed debug information during processing:
```bash
python track-name-fixer.py --debug
```

## Sonarr Integration

The Sonarr-enabled scripts support integration with your Sonarr instance to retrieve episode titles and ensure naming consistency. To use this feature:

1. Locate your Sonarr API key (Settings > General)
2. Use the `--sonarr_url` parameter to specify your Sonarr instance URL (e.g., http://localhost:8989)
3. Use the `--api_key` parameter with your Sonarr API key

With Sonarr integration enabled, the scripts can:
- Automatically fetch episode titles
- Ensure filenames match Sonarr's expected format
- Create files that will be correctly identified by Sonarr's import process

## Notes

- Always backup your files before processing
- Use the `--dry-run` option to preview changes before applying them
- Most scripts require FFmpeg to be installed and available in your PATH
- MKV manipulation scripts require MKVToolNix to be installed

## License

This collection of scripts is available under the MIT License.
