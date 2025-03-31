import concurrent.futures
from pathlib import Path
import os
import subprocess
import time
from datetime import datetime
import requests
import logging
from dotenv import load_dotenv
import platform

# Set up constants
SCRIPT_DIR = Path(__file__).parent
ERRORLOG = SCRIPT_DIR / "smart_test.log"
SMART_RESULTS_DIR = Path("/tmp/smart_results")

class SMARTTester:
    def __init__(self):
        self.setup_logging()
        self.load_config()
        self.os_type = platform.system().lower()
        
        # Create results directory if it doesn't exist
        SMART_RESULTS_DIR.mkdir(exist_ok=True)

    def setup_logging(self):
        try:
            logging.basicConfig(
                filename=ERRORLOG,
                level=logging.DEBUG,
                format='%(asctime)s - %(levelname)s - %(message)s',
                filemode='w'
            )
            logging.info("Logging initialized")
        except PermissionError:
            print(f"Permission denied when trying to write to {ERRORLOG}.")
            exit(1)

    def load_config(self):
        load_dotenv(SCRIPT_DIR / 'config.env')
        
        # Load required configuration
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        
        # Support multiple drives - parse comma-separated list from config
        drives_config = os.getenv('DRIVES', '/dev/sda')
        self.drives = [drive.strip() for drive in drives_config.split(',')]
        
        self.smart_timeout = int(os.getenv('SMART_TIMEOUT', '600'))  # Default to 600 seconds
        self.results_dir = Path(os.getenv('SMART_RESULTS_DIR', '/tmp/smart_results')) # Defaults to /tmp/smart_results
        
        # Validate configuration
        if not self.webhook_url:
            logging.error("Discord webhook URL is not set")
            exit(1)
        
        if not self.drives:
            logging.error("No drives specified for testing")
            exit(1)
        
        logging.info(f"Configuration loaded - Drives: {self.drives}, Timeout: {self.smart_timeout}s")

    def get_drive_type(self, device):
        """Determine if the device is SATA or NVMe"""
        try:
            if self.os_type == "linux":
                device_path = Path(f"/sys/block/{Path(device).name}")
                return "nvme" if "nvme" in device.lower() else "sata"
            elif self.os_type == "windows":
                cmd = f'Get-PhysicalDisk | Where-Object DeviceID -eq "{device}" | Select-Object BusType'
                result = self.run_command(['powershell', '-Command', cmd])
                return "nvme" if result and "NVMe" in result else "sata"
        except Exception as e:
            logging.error(f"Error determining drive type: {e}")
            return None

    def run_command(self, command):
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            logging.debug(f"Command output: {result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            logging.error(f"Command failed: {e.cmd} (code: {e.returncode})")
            return None

    def start_smart_test(self, drive):
        drive_type = self.get_drive_type(drive)
        if not drive_type:
            return False

        try:
            if drive_type == "nvme":
                if self.os_type == "linux":
                    return self.run_command(["nvme", "smart-log", drive])
                else:
                    return self.run_command([
                        "powershell", "-Command",
                        f"Get-PhysicalDisk | Where-Object DeviceID -eq '{drive}' | Get-StorageReliabilityCounter"
                    ])
            else:
                return self.run_command(["smartctl", "-t", "short", drive])
        except Exception as e:
            logging.error(f"Error starting SMART test for {drive}: {e}")
            return False

    def check_smart_test_status(self, drive):
        drive_type = self.get_drive_type(drive)
        if drive_type == "nvme":
            return True  # NVMe tests complete immediately
        
        status = self.run_command(["smartctl", "-c", drive])
        return "Self-test execution status:      (   0)" in status if status else False

    def wait_for_smart_test(self, drive):
        start_time = time.time()
        while time.time() - start_time < self.smart_timeout:
            if self.check_smart_test_status(drive):
                logging.info(f"SMART test completed successfully for {drive}")
                return True
            time.sleep(30)
        logging.error(f"SMART test for {drive} did not complete within {self.smart_timeout} seconds")
        return False

    def collect_smart_data(self, drive):
        drive_type = self.get_drive_type(drive)
        if not drive_type:
            return None

        # Create a unique filename based on the drive name
        drive_name = Path(drive).name
        results_path = SMART_RESULTS_DIR / f"smart_results_{drive_name}.txt"

        try:
            if drive_type == "nvme":
                if self.os_type == "linux":
                    result = self.run_command(["nvme", "smart-log", drive])
                else:
                    result = self.run_command([
                        "powershell", "-Command",
                        f"Get-PhysicalDisk | Where-Object DeviceID -eq '{drive}' | Get-StorageReliabilityCounter"
                    ])
            else:
                result = self.run_command(["smartctl", "-a", drive])

            if result:
                with open(results_path, 'w') as f:
                    f.write(result)
                return {"result": result, "path": results_path}
        except Exception as e:
            logging.error(f"Error collecting SMART data for {drive}: {e}")
            return None

    def parse_smart_results(self, results, drive_type):
        if drive_type == "nvme":
            important_sections = [
                "Critical Warning",
                "Temperature",
                "Available Spare",
                "Percentage Used",
                "Data Units Read",
                "Data Units Written",
                "Power Cycles",
                "Power On Hours",
                "Unsafe Shutdowns",
                "Media Errors"
            ]
        else:
            important_sections = [
                "SMART overall-health self-assessment test result",
                "SMART Attributes Data Structure revision number",
                "Vendor Specific SMART Attributes with Thresholds",
                "SMART Error Log Version",
                "SMART Self-test log structure revision number"
            ]

        return "\n".join([line for line in results.splitlines() 
                         if any(section in line for section in important_sections)])

    def send_discord_message(self, message, file_path=None):
        try:
            files = None
            if file_path and Path(file_path).exists():
                with open(file_path, "rb") as file:
                    files = {"file": file}
                    response = requests.post(self.webhook_url, data={"content": message}, files=files)
                    response.raise_for_status()
            else:
                response = requests.post(self.webhook_url, data={"content": message})
                response.raise_for_status()
            return True
        except requests.RequestException as e:
            logging.error(f"Failed to send Discord message: {str(e)}")
            return False
                
    def process_drive(self, drive):
        """Process a single drive's SMART test"""
        logging.info(f"Starting SMART test for {drive}")
        
        if not self.start_smart_test(drive):
            error_msg = f"Error: Failed to start SMART test on {drive}"
            logging.error(error_msg)
            self.send_discord_message(error_msg)
            return False

        if not self.wait_for_smart_test(drive):
            error_msg = f"Error: SMART test did not complete on {drive}"
            logging.error(error_msg)
            self.send_discord_message(error_msg)
            return False

        data = self.collect_smart_data(drive)
        if not data:
            error_msg = f"Error: Failed to collect SMART data for {drive}"
            logging.error(error_msg)
            self.send_discord_message(error_msg)
            return False

        drive_type = self.get_drive_type(drive)
        parsed_results = self.parse_smart_results(data["result"], drive_type)
        logging.info(f"Parsed SMART test results for {drive}")
        logging.info(parsed_results)

        message = (f"SMART log of {drive} ({drive_type.upper()}) on "
                  f"{os.uname().nodename if hasattr(os, 'uname') else platform.node()} "
                  f"at {datetime.now()}")
        
        self.send_discord_message(message, file_path=data["path"])
        return True

def main():
    tester = SMARTTester()
    logging.info("Script started")
    
    # Process all drives in parallel and track results
    results = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit all drive processing tasks
        future_to_drive = {executor.submit(tester.process_drive, drive): drive for drive in tester.drives}
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_drive):
            drive = future_to_drive[future]
            try:
                results[drive] = future.result()
                logging.info(f"Completed processing drive: {drive}")
            except Exception as e:
                logging.error(f"Error processing drive {drive}: {e}")
                results[drive] = False
    
    # Send a summary message
    total_drives = len(tester.drives)
    successful_tests = sum(1 for success in results.values() if success)
    
    summary = (f"SMART Test Summary: {successful_tests}/{total_drives} completed successfully\n"
              f"Host: {os.uname().nodename if hasattr(os, 'uname') else platform.node()}\n"
              f"Time: {datetime.now()}\n\n")
    
    for drive, success in results.items():
        summary += f"- {drive}: {'✅ Success' if success else '❌ Failed'}\n"
    
    tester.send_discord_message(summary)
    logging.info("Script completed")

if __name__ == "__main__":
    main()
