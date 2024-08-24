#!/bin/bash

# Check if the input folder is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <input_folder>"
  exit 1
fi

input_folder=$1

# Create an output folder
output_folder="${input_folder}/converted"
mkdir -p "$output_folder"

# Loop through all HEIC files in the input folder
for heic_file in "$input_folder"/*.HEIC "$input_folder"/*.heic; do
  if [ -f "$heic_file" ]; then
    # Get the base name of the file
    base_name=$(basename "$heic_file" .HEIC)
    base_name=$(basename "$base_name" .heic)

    # Convert to JPG using heif-convert and ImageMagick
    heif-convert "$heic_file" "$output_folder/${base_name}.jpg"
  fi
done

echo "Conversion complete. JPG files are saved in $output_folder"
