#!/bin/bash

# Check if the input folder is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <input_folder>"
  exit 1
fi

input_folder=$1

# Create an output folder for images that are not at 0 degrees
output_folder="${input_folder}/not_0_degrees"
mkdir -p "$output_folder"

# Loop through all JPG files in the input folder
for jpg_file in "$input_folder"/*.jpg "$input_folder"/*.jpeg; do
  if [ -f "$jpg_file" ]; then
    # Get the orientation of the image using ImageMagick's identify command
    orientation=$(identify -format '%[EXIF:Orientation]' "$jpg_file")

    # Move the file if it is not at 0 degrees (Orientation 1 is 0 degrees)
    if [ "$orientation" != "1" ]; then
      mv "$jpg_file" "$output_folder"
    fi
  fi
done

echo "Check complete. Non-0-degree images are moved to $output_folder"
