#!/usr/bin/env python3

import os
import sys
import subprocess
import yaml
from typing import List, Dict, Optional, Set


class DockerComposeManager:
    """Manages Docker Compose services interactively."""

    def __init__(self):
        self.compose_file = self._find_compose_file()
        self.services = self._parse_services()

    def _find_compose_file(self) -> str:
        """Find a Docker Compose file in the current directory."""
        possible_files = [
            "compose.yml",
            "compose.yaml",
            "docker-compose.yml",
            "docker-compose.yaml"
        ]

        for file in possible_files:
            if os.path.isfile(file):
                print(f"Found Docker Compose file: {file}")
                return file

        print("Error: No Docker Compose file found in the current directory.")
        print("Looked for: compose.yml, compose.yaml, docker-compose.yml, docker-compose.yaml")
        sys.exit(1)

    def _parse_services(self) -> Dict[str, Dict]:
        """Parse the Docker Compose file and extract services."""
        try:
            with open(self.compose_file, 'r') as file:
                compose_data = yaml.safe_load(file)
                
            # Handle different Docker Compose versions
            if 'services' in compose_data:
                return compose_data['services']
            else:
                # For older Docker Compose formats
                return {k: v for k, v in compose_data.items() if isinstance(v, dict) and not k.startswith('_')}
                
        except Exception as e:
            print(f"Error parsing Docker Compose file: {e}")
            sys.exit(1)

    def get_running_services(self) -> Set[str]:
        """Get the list of currently running services."""
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", self.compose_file, "ps", "--services"],
                capture_output=True,
                text=True,
                check=True
            )
            return set(result.stdout.strip().split('\n')) if result.stdout.strip() else set()
        except subprocess.CalledProcessError:
            # If the command fails, assume no services are running
            return set()

    def stop_all_services(self):
        """Stop all running Docker Compose services."""
        running_services = self.get_running_services()
        if running_services:
            print("Stopping running services...")
            try:
                subprocess.run(
                    ["docker", "compose", "-f", self.compose_file, "down"],
                    check=True
                )
                print("All services stopped successfully.")
            except subprocess.CalledProcessError as e:
                print(f"Error stopping services: {e}")
                sys.exit(1)
        else:
            print("No running services to stop.")

    def start_services(self, services: List[str]):
        """Start the specified Docker Compose services."""
        if not services:
            print("No services selected to start.")
            return

        try:
            cmd = ["docker", "compose", "-f", self.compose_file, "up", "-d"]
            cmd.extend(services)
            
            print(f"Starting services: {', '.join(services)}...")
            subprocess.run(cmd, check=True)
            print("Services started successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error starting services: {e}")
            sys.exit(1)

    def display_service_logs(self, services: List[str], follow: bool = True):
        """Display logs for the specified services."""
        if not services:
            return

        try:
            cmd = ["docker", "compose", "-f", self.compose_file, "logs"]
            if follow:
                cmd.append("-f")
            cmd.extend(services)
            
            print(f"Displaying logs for: {', '.join(services)}...")
            subprocess.run(cmd)
        except KeyboardInterrupt:
            print("\nStopped following logs.")
        except subprocess.CalledProcessError as e:
            print(f"Error displaying logs: {e}")

    def interactive_service_selection(self) -> List[str]:
        """Interactively select services to start."""
        if not self.services:
            print("No services found in the Docker Compose file.")
            sys.exit(1)

        print("\nAvailable services:")
        service_list = list(self.services.keys())
        
        for i, service in enumerate(service_list, 1):
            print(f"{i}. {service}")
        
        print("\nSelect services to start (comma-separated numbers, 'all' for all services):")
        selection = input("> ").strip()
        
        if selection.lower() == 'all':
            return service_list
        
        try:
            selected_indices = [int(idx.strip()) - 1 for idx in selection.split(',') if idx.strip()]
            selected_services = [service_list[idx] for idx in selected_indices if 0 <= idx < len(service_list)]
            
            if not selected_services:
                print("No valid services selected.")
                return self.interactive_service_selection()
                
            return selected_services
        except (ValueError, IndexError):
            print("Invalid selection. Please try again.")
            return self.interactive_service_selection()


def main():
    """Main function to run the Docker Compose service manager."""
    print("Docker Compose Service Manager")
    print("==============================")
    
    manager = DockerComposeManager()
    
    # Get running services
    running_services = manager.get_running_services()
    if running_services:
        print(f"Currently running services: {', '.join(running_services)}")
    else:
        print("No services are currently running.")
    
    # Select services to start
    selected_services = manager.interactive_service_selection()
    print(f"Selected services: {', '.join(selected_services)}")
    
    # Stop running services
    manager.stop_all_services()
    
    # Start selected services
    manager.start_services(selected_services)
    
    # Ask if user wants to see logs
    print("\nDo you want to see the logs? (y/n)")
    if input("> ").strip().lower() == 'y':
        manager.display_service_logs(selected_services)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)