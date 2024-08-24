import subprocess
import os
from tqdm import tqdm

def check_nvidia_gpu():
    """Check if NVIDIA GPU is available."""
    try:
        subprocess.run(["nvidia-smi", "-L"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def check_intel_qsv():
    """Check if Intel QSV is supported."""
    try:
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-v", "error", "-init_hw_device", "qsv=qsv:hw", "-f", "lavfi", "-i", "nullsrc", "-f", "null", "-"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except subprocess.CalledProcessError:
        return False

def convert_to_hevc(input_file):
    """Convert video stream to HEVC with fallback for hardware encoding."""
    output_file = f"{os.path.splitext(input_file)[0]}_hevc.mkv"

    if check_nvidia_gpu():
        print(f"NVIDIA GPU found. Using NVENC for {os.path.basename(input_file)}.")
        video_encoder = "hevc_nvenc"
        preset = "p7"
    elif check_intel_qsv():
        print(f"Intel QSV found. Using QSV for {os.path.basename(input_file)}.")
        video_encoder = "hevc_qsv"
        preset = None  # QSV doesn't need a preset
    else:
        print(f"No hardware encoder found. Falling back to software encoding (libx265) for {os.path.basename(input_file)}.")
        video_encoder = "libx265"
        preset = "medium"

    command = ["ffmpeg", "-i", input_file, "-c:v", video_encoder]

    if preset:
        command.extend(["-preset", preset])
        
    command.extend(["-b:v", "2M", "-c:a", "copy", "-c:s", "copy", "-map_chapters", "0", output_file])

    # Run the command with a progress bar
    try:
        with tqdm(total=100, desc=os.path.basename(input_file), unit="%", ncols=100) as pbar:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            for line in process.stdout:
                if "frame=" in line:
                    progress = parse_progress(line)
                    pbar.update(progress - pbar.n)
            process.wait()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, command)
    except KeyboardInterrupt:
        print(f"\nConversion interrupted. Deleting incomplete file: {output_file}")
        if os.path.exists(output_file):
            os.remove(output_file)
        raise  # Re-raise the exception to exit the script
    except subprocess.CalledProcessError as e:
        print(f"Error during conversion of {os.path.basename(input_file)}: {e}")

def parse_progress(ffmpeg_output_line):
    """Parse progress percentage from ffmpeg output."""
    if "time=" in ffmpeg_output_line:
        time_str = ffmpeg_output_line.split("time=")[1].split(" ")[0]
        time_parts = list(map(float, time_str.split(":")))
        seconds = time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]
        return int((seconds / total_duration) * 100)
    return 0

def get_total_duration(input_file):
    """Get the total duration of the video in seconds."""
    result = subprocess.run(
        ["ffmpeg", "-i", input_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    for line in result.stdout.splitlines():
        if "Duration" in line:
            time_str = line.split("Duration: ")[1].split(",")[0]
            time_parts = list(map(float, time_str.split(":")))
            return time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]
    return 0

def process_folder(folder_path):
    """Process all MKV files in the given folder."""
    mkv_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".mkv")]

    if not mkv_files:
        print("No MKV files found in the folder.")
        return

    for input_file in mkv_files:
        global total_duration
        total_duration = get_total_duration(input_file)
        convert_to_hevc(input_file)

if __name__ == "__main__":
    folder_path = input("Enter the path to the folder containing MKV files: ")
    if not os.path.isdir(folder_path):
        print(f"Folder not found: {folder_path}")
    else:
        try:
            process_folder(folder_path)
        except KeyboardInterrupt:
            print("Bulk conversion interrupted.")
