#!/usr/bin/env python3
import hashlib
import os
from tqdm import tqdm

def get_file_hash(file_path, hash_algo='sha256'):
    """Calculate the hash of a file."""
    hash_obj = hashlib.new(hash_algo)
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

def get_folder_hashes(folder_path, hash_algo='sha256'):
    """Get a dictionary of file hashes for all files in a folder."""
    file_hashes = {}
    file_list = []

    # Collect all files in the folder
    for root, _, files in os.walk(folder_path):
        for file_name in files:
            file_list.append(os.path.join(root, file_name))
    
    # Iterate through the files with a progress bar
    for file_path in tqdm(file_list, desc=f"Processing {folder_path}", unit="file"):
        file_hash = get_file_hash(file_path, hash_algo)
        file_hashes[file_path] = file_hash
    
    return file_hashes

def find_duplicates(folder1, folder2, hash_algo='sha256'):
    """Find and count duplicate files between two folders based on their hashes."""
    folder1_hashes = get_folder_hashes(folder1, hash_algo)
    folder2_hashes = get_folder_hashes(folder2, hash_algo)

    duplicates = 0

    print("\nComparing files for duplicates...\n")
    
    # Check for duplicates in folder2 compared to folder1 with progress
    for file2_path, file2_hash in tqdm(folder2_hashes.items(), desc="Comparing hashes", unit="file"):
        if file2_hash in folder1_hashes.values():
            print(f"Duplicate found: {file2_path}")
            duplicates += 1

    print(f"\nTotal duplicates found: {duplicates}")

# Usage
folder1_path = '/mnt/data/Pictures'
folder2_path = '/mnt/data/Pictures_OLD'
find_duplicates(folder1_path, folder2_path)
