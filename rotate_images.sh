#!/bin/bash

# Check if the input folder is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <input_folder> <rotation_degree>"
  exit 1
fi

input_folder=$1
rotation_degree=$2

# Create an output folder
output_folder="${input_folder}/rotated"
mkdir -p "$output_folder"

# Loop through all JPG files in the input folder
for jpg_file in "$input_folder"/*.jpg "$input_folder"/*.jpeg; do
  if [ -f "$jpg_file" ]; then
    # Get the base name of the file
    base_name=$(basename "$jpg_file")
    
    # Rotate the image using ImageMagick
    convert "$jpg_file" -rotate "$rotation_degree" "$output_folder/$base_name"
  fi
done

echo "Rotation complete. Rotated images are saved in $output_folder"
