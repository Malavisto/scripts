#!/bin/bash

# Check if input file is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <input_mkv_file>"
    exit 1
fi

input_file="$1"
output_dir="extracted_audio"
mkdir -p "$output_dir"

# Get the number of audio tracks
audio_tracks=$(ffmpeg -i "$input_file" 2>&1 | grep -c 'Audio')

echo "Found $audio_tracks audio tracks in $input_file."

# Extract each audio track
for ((i=0; i<audio_tracks; i++)); do
    output_file="$output_dir/audio_track_$i.ac3"
    ffmpeg -i "$input_file" -map 0:a:$i -c:a copy "$output_file"
    echo "Extracted audio track $i to $output_file."
done

echo "Extraction complete. All audio tracks are saved in the '$output_dir' directory."
