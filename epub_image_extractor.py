import os
import re
import zipfile
from datetime import datetime
import ebooklib
from ebooklib import epub
from PIL import Image
import io
import logging
import sys
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.expanduser("~/scripts/epub_extractor.log"))
    ]
)
logger = logging.getLogger("epub_extractor")

def sanitize_filename(filename):
    """
    Sanitize filename to remove or replace problematic characters.
    
    Args:
        filename (str): Original filename
    
    Returns:
        str: Sanitized filename
    """
    # Remove or replace characters that are problematic in filenames
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit filename length
    return sanitized[:255]

def extract_images_from_epub(epub_path):
    """
    Extract all images from an EPUB file.
    
    Args:
        epub_path (str): Path to the EPUB file
    
    Returns:
        list: List of tuples (image, filename)
    """
    logger.info(f"Extracting images from: {epub_path}")
    try:
        # Read the EPUB file
        book = epub.read_epub(epub_path)
        
        # List to store images
        extracted_images = []
        
        # Counter to ensure unique filenames
        image_counter = 1
        
        # Get total number of items for progress reporting
        total_items = len(list(book.get_items()))
        processed_items = 0
        image_items = 0
        
        # Extract all image items
        for item in book.get_items():
            processed_items += 1
            if processed_items % 50 == 0 or processed_items == total_items:
                logger.info(f"Processing EPUB content: {processed_items}/{total_items} items")
            
            if item.get_type() == ebooklib.ITEM_IMAGE:
                image_items += 1
                try:
                    # Open the image
                    image = Image.open(io.BytesIO(item.get_content()))
                    
                    # Generate a unique filename
                    book_name = sanitize_filename(os.path.splitext(os.path.basename(epub_path))[0])
                    
                    # Determine file extension
                    file_ext = os.path.splitext(item.get_name())[1].lower()
                    if not file_ext:
                        # Default to .jpg if no extension
                        file_ext = '.jpg'
                    
                    # Ensure the extension matches the actual image format
                    if file_ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
                        # Use a default extension based on image format
                        if image.format:
                            file_ext = f'.{image.format.lower()}'
                        else:
                            file_ext = '.jpg'
                    
                    filename = f"{book_name}_image_{image_counter:03d}{file_ext}"
                    logger.debug(f"Found image: {filename} (Mode: {image.mode}, Size: {image.size})")
                    
                    extracted_images.append((image, filename))
                    image_counter += 1
                    
                except Exception as img_error:
                    logger.error(f"Error processing image #{image_items} in {epub_path}: {img_error}")
                    logger.debug(traceback.format_exc())
        
        logger.info(f"Found {len(extracted_images)} images in {epub_path}")
        return extracted_images
    
    except Exception as e:
        logger.error(f"Error processing {epub_path}: {e}")
        logger.debug(traceback.format_exc())
        return []

def find_epub_files(book_dir):
    """
    Recursively find EPUB files in a directory.
    
    Args:
        book_dir (str): Root directory to search for EPUB files
    
    Returns:
        list: List of full paths to EPUB files
    """
    logger.info(f"Searching for EPUB files in: {book_dir}")
    epub_files = []
    for root, dirs, files in os.walk(book_dir):
        for file in files:
            # Check file extensions for various EPUB formats
            if file.lower().endswith(('.epub', '.epub3')):
                epub_files.append(os.path.join(root, file))
    
    logger.info(f"Found {len(epub_files)} EPUB files")
    return epub_files

def organize_epub_images(input_dir, output_dir, backup_dir):
    """
    Extract and organize all images from EPUB files in a directory.
    
    Args:
        input_dir (str): Directory containing book folders
        output_dir (str): Directory to save extracted images
        backup_dir (str): Directory to store backup archives
    """
    start_time = datetime.now()
    logger.info(f"Starting EPUB image extraction process")
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Backup directory: {backup_dir}")
    
    # Create directories if they don't exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(backup_dir, exist_ok=True)
    
    # Counters for tracking
    processed_count = 0
    image_count = 0
    skipped_count = 0
    error_count = 0
    
    # Timestamp for unique backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Find all EPUB files
    epub_files = find_epub_files(input_dir)
    total_files = len(epub_files)
    
    if total_files == 0:
        logger.warning("No EPUB files found. Exiting.")
        return
    
    # Iterate through all EPUB files
    for file_index, epub_path in enumerate(epub_files, 1):
        try:
            # Extract book name from path
            book_name = sanitize_filename(os.path.basename(os.path.dirname(epub_path)))
            logger.info(f"Processing file {file_index}/{total_files}: {book_name} ({epub_path})")
            
            # Extract images
            extracted_images = extract_images_from_epub(epub_path)
            
            if extracted_images:
                # Create a subdirectory for this book's images
                book_output_dir = os.path.join(output_dir, book_name)
                os.makedirs(book_output_dir, exist_ok=True)
                
                # Save each image
                for img_index, (image, img_filename) in enumerate(extracted_images, 1):
                    output_path = os.path.join(book_output_dir, img_filename)
                    logger.debug(f"Saving image {img_index}/{len(extracted_images)}: {img_filename}")
                    
                    # Optional: Resize large images (uncomment and adjust as needed)
                    # max_size = (1024, 1024)
                    # image.thumbnail(max_size)
                    
                    try:
                        # Handle RGBA images when saving as JPEG
                        if image.mode == 'RGBA' and output_path.lower().endswith(('.jpg', '.jpeg')):
                            logger.debug(f"Converting RGBA to RGB for JPEG: {img_filename}")
                            # Convert RGBA to RGB by removing alpha channel
                            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                            rgb_image.paste(image, mask=image.split()[3])  # Use alpha channel as mask
                            rgb_image.save(output_path)
                        else:
                            # Save the image in its original format
                            image.save(output_path)
                        
                        image_count += 1
                    except Exception as save_error:
                        logger.error(f"Error saving image {img_filename}: {save_error}")
                        # Try alternative approach for problematic images
                        try:
                            logger.info(f"Attempting fallback conversion for {img_filename}")
                            # Convert to RGB as a fallback for any problematic image
                            rgb_image = image.convert('RGB')
                            rgb_image.save(output_path)
                            image_count += 1
                            logger.info(f"Successfully saved {img_filename} after conversion to RGB")
                        except Exception as fallback_error:
                            logger.error(f"Failed to save image {img_filename} even after conversion: {fallback_error}")
                            logger.debug(traceback.format_exc())
                            error_count += 1
                
                processed_count += 1
                logger.info(f"Processed {len(extracted_images)} images for: {book_name}")
            else:
                skipped_count += 1
                logger.info(f"No images found for: {book_name}")
        
        except Exception as book_error:
            logger.error(f"Error processing book file {epub_path}: {book_error}")
            logger.debug(traceback.format_exc())
            error_count += 1
            # Continue with the next file
            continue
    
    # Create backup archive if images were extracted
    if image_count > 0:
        try:
            logger.info("Creating backup archive...")
            backup_filename = f"epub_images_backup_{timestamp}.zip"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Create a zip archive of the entire output directory
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                file_count = 0
                for root, dirs, files in os.walk(output_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, output_dir)
                        zipf.write(file_path, arcname=arcname)
                        file_count += 1
                        if file_count % 100 == 0:
                            logger.info(f"Backed up {file_count} files so far...")
            
            logger.info(f"Backup archive created: {backup_path} with {file_count} files")
        except Exception as backup_error:
            logger.error(f"Error creating backup: {backup_error}")
            logger.debug(traceback.format_exc())
    else:
        logger.warning("No images were extracted, skipping backup creation")
    
    # Calculate elapsed time
    end_time = datetime.now()
    elapsed_time = end_time - start_time
    
    # Print summary
    summary = f"""
Summary:
-----------------------------------------
Total EPUB files found:       {total_files}
Books with images extracted:  {processed_count}
Books with no images:         {skipped_count}
Books with errors:            {error_count}
Total images extracted:       {image_count}
Processing time:              {elapsed_time}
-----------------------------------------
"""
    logger.info(summary)

def manage_backups(backup_dir, max_backups=5):
    """
    Manage backup archives, keeping only the most recent backups.
    
    Args:
        backup_dir (str): Directory containing backup archives
        max_backups (int): Maximum number of backup archives to keep
    """
    logger.info(f"Managing backups in {backup_dir} (keeping {max_backups} most recent)")
    try:
        # Get all backup files, sorted by modification time (newest first)
        backup_files = sorted(
            [f for f in os.listdir(backup_dir) if f.startswith('epub_images_backup_') and f.endswith('.zip')],
            key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)),
            reverse=True
        )
        
        logger.info(f"Found {len(backup_files)} backup archives")
        
        # Remove older backups if exceeding max_backups
        if len(backup_files) > max_backups:
            for old_backup in backup_files[max_backups:]:
                try:
                    backup_path = os.path.join(backup_dir, old_backup)
                    os.remove(backup_path)
                    logger.info(f"Removed old backup: {old_backup}")
                except Exception as e:
                    logger.error(f"Error removing old backup {old_backup}: {e}")
        else:
            logger.info(f"No backups need to be removed (have {len(backup_files)}, keeping {max_backups})")
    except Exception as e:
        logger.error(f"Error managing backups: {e}")
        logger.debug(traceback.format_exc())

# Example usage
if __name__ == "__main__":
    try:
        # Paths based on your directory structure
        input_directory = os.path.expanduser("~/Backups/Books")
        output_directory = os.path.expanduser("~/Backups/BookImages")
        backup_directory = os.path.expanduser("~/Backups/ImageBackups")
        
        # Extract images and create backup
        organize_epub_images(input_directory, output_directory, backup_directory)
        
        # Manage backups (optional)
        manage_backups(backup_directory)
        
        logger.info("Script completed successfully")
    except Exception as e:
        logger.critical(f"Unhandled exception in main script: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)

# Note: You'll need to install required libraries:
# pip install ebooklib Pillow