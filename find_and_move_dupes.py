import hashlib
import os
import shutil
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

def move_duplicate(file_path, dump_folder, folder2_path):
    """Move the duplicate file to the dump folder, maintaining the subfolder structure."""
    # Create the relative path by stripping the folder2_path from the file_path
    relative_path = os.path.relpath(file_path, folder2_path)
    
    # Determine the target path in the dump folder
    target_path = os.path.join(dump_folder, relative_path)
    
    # Ensure the target directory exists
    target_dir = os.path.dirname(target_path)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    # Move the file
    shutil.move(file_path, target_path)
    print(f"Moved duplicate: {file_path} to {target_path}")

def find_and_move_duplicates(folder1, folder2, dump_folder, hash_algo='sha256'):
    """Find and move duplicate files from folder2 to the dump folder, maintaining subfolder structure."""
    folder1_hashes = get_folder_hashes(folder1, hash_algo)
    folder2_hashes = get_folder_hashes(folder2, hash_algo)

    duplicates = 0

    print("\nComparing files for duplicates...\n")
    
    # Check for duplicates in folder2 compared to folder1 with progress
    for file2_path, file2_hash in tqdm(folder2_hashes.items(), desc="Comparing hashes", unit="file"):
        if file2_hash in folder1_hashes.values():
            move_duplicate(file2_path, dump_folder, folder2)
            duplicates += 1

    print(f"\nTotal duplicates moved: {duplicates}")

# Usage
folder1_path = '/mnt/data/Pictures'
folder2_path = '/mnt/data/Pictures_OLD'
dump_folder = '/mnt/data/Pictures_DUMP'
find_and_move_duplicates(folder1_path, folder2_path, dump_folder)
