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
ERRORLOG = SCRIPT_DIR / "smart_test_error.log"
SMART_RESULTS = Path("/tmp/smart_results.txt")

class SMARTTester:
    def __init__(self):
        self.setup_logging()
        self.load_config()
        self.os_type = platform.system().lower()

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
        self.drive = os.getenv('DRIVE', '/dev/sda')  # Default to /dev/sda if not specified
        self.smart_timeout = int(os.getenv('SMART_TIMEOUT', '600'))  # Default to 600 seconds
        self.results_path = Path(os.getenv('SMART_RESULTS', '/tmp/smart_results.txt'))
        
        # Validate configuration
        if not self.webhook_url:
            logging.error("Discord webhook URL is not set")
            exit(1)
        
        logging.info(f"Configuration loaded - Drive: {self.drive}, Timeout: {self.smart_timeout}s")

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

    def start_smart_test(self):
        drive_type = self.get_drive_type(self.drive)
        if not drive_type:
            return False

        try:
            if drive_type == "nvme":
                if self.os_type == "linux":
                    return self.run_command(["nvme", "smart-log", self.drive])
                else:
                    return self.run_command([
                        "powershell", "-Command",
                        f"Get-PhysicalDisk | Where-Object DeviceID -eq '{self.drive}' | Get-StorageReliabilityCounter"
                    ])
            else:
                return self.run_command(["smartctl", "-t", "short", self.drive])
        except Exception as e:
            logging.error(f"Error starting SMART test: {e}")
            return False

    def check_smart_test_status(self):
        drive_type = self.get_drive_type(self.drive)
        if drive_type == "nvme":
            return True  # NVMe tests complete immediately
        
        status = self.run_command(["smartctl", "-c", self.drive])
        return "Self-test execution status:      (   0)" in status if status else False

    def wait_for_smart_test(self):
        start_time = time.time()
        while time.time() - start_time < self.smart_timeout:
            if self.check_smart_test_status():
                logging.info("SMART test completed successfully")
                return True
            time.sleep(30)
        logging.error(f"SMART test did not complete within {self.smart_timeout} seconds")
        return False

    def collect_smart_data(self):
        drive_type = self.get_drive_type(self.drive)
        if not drive_type:
            return None

        try:
            if drive_type == "nvme":
                if self.os_type == "linux":
                    result = self.run_command(["nvme", "smart-log", self.drive])
                else:
                    result = self.run_command([
                        "powershell", "-Command",
                        f"Get-PhysicalDisk | Where-Object DeviceID -eq '{self.drive}' | Get-StorageReliabilityCounter"
                    ])
            else:
                result = self.run_command(["smartctl", "-a", self.drive])

            if result:
                with open(self.results_path, 'w') as f:
                    f.write(result)
                return result
        except Exception as e:
            logging.error(f"Error collecting SMART data: {e}")
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
            files = {"file": open(file_path, "rb")} if file_path and Path(file_path).exists() else None
            response = requests.post(self.webhook_url, data={"content": message}, files=files)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logging.error(f"Failed to send Discord message: {str(e)}")
            return False
        finally:
            if files:
                files["file"].close()

def main():
    tester = SMARTTester()
    logging.info("Script started")

    if not tester.start_smart_test():
        tester.send_discord_message(f"Error: Failed to start SMART test on {tester.drive}")
        return

    if not tester.wait_for_smart_test():
        tester.send_discord_message(f"Error: SMART test did not complete on {tester.drive}")
        return

    results = tester.collect_smart_data()
    if not results:
        tester.send_discord_message(f"Error: Failed to collect SMART data for {tester.drive}")
        return

    drive_type = tester.get_drive_type(tester.drive)
    parsed_results = tester.parse_smart_results(results, drive_type)
    logging.info("Parsed SMART test results")
    logging.info(parsed_results)

    message = (f"SMART log of {tester.drive} ({drive_type.upper()}) on "
              f"{os.uname().nodename if hasattr(os, 'uname') else platform.node()} "
              f"at {datetime.now()}")
    tester.send_discord_message(message, file_path=tester.results_path)

    logging.info("Script completed")

if __name__ == "__main__":
    main()