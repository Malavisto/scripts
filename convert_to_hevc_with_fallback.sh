#!/bin/bash

# Check if the input file is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <input_file>"
    exit 1
fi

# Input file
input_file="$1"

# Output file (same name with "_hevc" appended before the extension)
output_file="${input_file%.*}_hevc.mkv"

# Function to check for NVIDIA GPU
function check_nvidia_gpu {
    if command -v nvidia-smi &> /dev/null; then
        nvidia-smi -L &> /dev/null
        return $?
    else
        return 1
    fi
}

# Function to check for Intel QSV support
function check_intel_qsv {
    ffmpeg -hide_banner -v error -init_hw_device qsv=qsv:hw -f lavfi -i nullsrc -f null - &> /dev/null
    return $?
}

# Determine which encoder to use based on the available hardware
if check_nvidia_gpu; then
    echo "NVIDIA GPU found. Using NVENC."
    video_encoder="hevc_nvenc"
    preset="p7"  # Default preset for NVENC (you can adjust this)
elif check_intel_qsv; then
    echo "Intel QSV found. Using QSV."
    video_encoder="hevc_qsv"
    preset=""  # QSV doesn't always need a preset
else
    echo "No hardware encoder found. Falling back to software encoding (libx265)."
    video_encoder="libx265"
    preset="slow"  # Default preset for libx265
fi

# Convert the video stream to HEVC using the appropriate encoder
if [ "$video_encoder" == "hevc_qsv" ]; then
    ffmpeg -i "$input_file" -c:v $video_encoder -b:v 5M -c:a copy -c:s copy -map_chapters 0 "$output_file"
else
    ffmpeg -i "$input_file" -c:v $video_encoder -preset $preset -b:v 5M -c:a copy -c:s copy -map_chapters 0 "$output_file"
fi

echo "Conversion complete: $output_file"
