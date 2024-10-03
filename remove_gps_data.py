import os
from PIL import Image
import piexif

def remove_gps_exif(image_path, output_path):
    img = Image.open(image_path)
    exif_data = img.info.get('exif')
    
    if exif_data:
        # Load the EXIF data and remove GPS info if it exists
        exif_dict = piexif.load(exif_data)
        exif_dict.pop('GPS', None)  # Remove GPS data
        
        # Dump new EXIF data without GPS
        new_exif_data = piexif.dump(exif_dict)
        
        # Save the image without GPS metadata
        img.save(output_path, exif=new_exif_data)
        print(f"Processed {image_path}, GPS data removed.")
    else:
        print(f"No EXIF data found in {image_path}. Skipping...")

def process_images(folder):
    for filename in os.listdir(folder):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            image_path = os.path.join(folder, filename)
            output_path = os.path.join(folder, f"no_gps_{filename}")
            remove_gps_exif(image_path, output_path)

if __name__ == "__main__":
    folder = "/home/techkid/Photos-001"  # Replace with your images folder
    process_images(folder)
