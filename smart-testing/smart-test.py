from pathlib import Path
import os
import subprocess
import time
from datetime import datetime
import requests
import logging
from dotenv import load_dotenv

# Set up constants
SCRIPT_DIR = Path(__file__).parent
ERRORLOG = SCRIPT_DIR / "smart_test_error.log"
BASH_SCRIPT = SCRIPT_DIR / "smart_data_collection.sh"
SMART_RESULTS = Path("/tmp/smart_results.txt")
DRIVE = "/dev/sda"

def setup_logging():
    try:
        logging.basicConfig(filename=ERRORLOG, level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - %(message)s',
                            filemode='w')  # Overwrite the log file
        logging.info("Logging initialized")
    except PermissionError:
        print(f"Permission denied when trying to write to {ERRORLOG}.")
        exit(1)

# Call the setup_logging function
setup_logging()

# Load environment variables
load_dotenv(SCRIPT_DIR / 'config.env')
WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

def send_discord_message(message, file_path=None):
    if not WEBHOOK_URL:
        logging.error("Discord webhook URL is not set")
        return False

    try:
        files = {"file": open(file_path, "rb")} if file_path and Path(file_path).exists() else None
        response = requests.post(WEBHOOK_URL, data={"content": message}, files=files)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        logging.error(f"Failed to send Discord message: {str(e)}")
        return False
    finally:
        if files:
            files["file"].close()

def run_command(command):
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logging.debug(f"Command output: {result.stdout}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {e.cmd} (code: {e.returncode})")
        return None

def start_smart_test():
    return run_command(["smartctl", "-t", "short", DRIVE])

def check_smart_test_status():
    status = run_command(["smartctl", "-c", DRIVE])
    return "Self-test execution status:      (   0)" in status if status else False

def wait_for_smart_test(timeout=600):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if check_smart_test_status():
            logging.info("SMART test completed successfully")
            return True
        time.sleep(30)
    logging.error(f"SMART test did not complete within {timeout} seconds")
    return False

def run_bash_script():
    try:
        subprocess.run(["sudo", "bash", str(BASH_SCRIPT)], check=True)
        logging.info("Bash script executed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Bash script failed: {e}")
        return False

def read_smart_results():
    try:
        with open(SMART_RESULTS, 'r') as file:
            return file.read()
    except IOError as e:
        logging.error(f"Error reading SMART results: {e}")
        return None

def parse_smart_results(results):
    important_sections = [
        "SMART overall-health self-assessment test result",
        "SMART Attributes Data Structure revision number",
        "Vendor Specific SMART Attributes with Thresholds",
        "SMART Error Log Version",
        "SMART Self-test log structure revision number",
        "SMART Selective self-test log data structure revision number"
    ]
    return "\n".join([line for line in results.splitlines() if any(section in line for section in important_sections)])

def main():
    logging.info("Script started")

    if not WEBHOOK_URL:
        logging.error("WEBHOOK_URL is not set. Check your config.env file.")
        return

    if not start_smart_test():
        send_discord_message(f"Error: Failed to start SMART test on {DRIVE}")
        return

    if not wait_for_smart_test():
        send_discord_message(f"Error: SMART test did not complete on {DRIVE}")
        return

    if not run_bash_script():
        send_discord_message("Error: Failed to run SMART data collection script.")
        return

    results = read_smart_results()
    if not results:
        send_discord_message("Error: Failed to read SMART test results.")
        return

    parsed_results = parse_smart_results(results)
    logging.info("Parsed SMART test results")
    logging.info(parsed_results)

    send_discord_message(f"SMART log of {DRIVE} on {os.uname().nodename} at {datetime.now()}:", file_path=SMART_RESULTS)

    logging.info("Script completed")

if __name__ == "__main__":
    main()