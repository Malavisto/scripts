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

def convert_to_hevc(input_file, output_file):
    """Convert video stream to HEVC with fallback for hardware encoding."""
    if check_nvidia_gpu():
        print(f"NVIDIA GPU found. Using NVENC for {os.path.basename(input_file)}.")
        video_encoder = "hevc_nvenc"
        preset = "q7"
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
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        with tqdm(desc=os.path.basename(input_file), unit="%", ncols=100) as pbar:
            for line in process.stdout:
                if "frame=" in line:
                    progress = parse_progress(line)
                    if progress is not None:
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
    return None

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

def process_folder(source_folder, output_folder):
    """Process all MKV files in the given folder, preserving folder structure."""
    for root, dirs, files in os.walk(source_folder):
        for file in files:
            if file.endswith(".mkv"):
                input_file = os.path.join(root, file)
                relative_path = os.path.relpath(root, source_folder)
                output_dir = os.path.join(output_folder, relative_path)
                os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(output_dir, f"{os.path.splitext(file)[0]}_hevc.mkv")
                global total_duration
                total_duration = get_total_duration(input_file)
                convert_to_hevc(input_file, output_file)

if __name__ == "__main__":
    source_folder = input("Enter the path to the source folder containing MKV files: ")
    output_folder = input("Enter the path to the output folder: ")

    if not os.path.isdir(source_folder):
        print(f"Source folder not found: {source_folder}")
    elif not os.path.isdir(output_folder):
        print(f"Output folder not found: {output_folder}")
    else:
        try:
            process_folder(source_folder, output_folder)
        except KeyboardInterrupt:
            print("Bulk conversion interrupted.")
