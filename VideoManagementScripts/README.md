# Video Management Scripts

A collection of Python scripts for managing, processing, and organizing video files and related media.

## Overview

This repository contains various utility scripts for managing video files, including renaming episodes, merging media elements (video, audio, subtitles), organizing files, and processing subtitles.

## Requirements

- Python 3.6+
- FFmpeg (required for most scripts)
- ffprobe (component of FFmpeg, used for media analysis)

## Scripts

### 1. file-renamer.py

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

### 2. remove_pgs_subs.py

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

### 3. subtitle_rename.py

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

### 4. video-extract.py

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

## Notes

- Always backup your files before processing
- Use the `--dry-run` option to preview changes before applying them
- Most scripts require FFmpeg to be installed and available in your PATH

## License

This collection of scripts is available under the MIT License.
