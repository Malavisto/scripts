#!/usr/bin/env python3
"""
Docker Stats TUI - A terminal-based UI for monitoring Docker container stats
"""

import os
import sys
import time
import json
import subprocess
import curses
import yaml
from datetime import datetime

class DockerStatsTUI:
    def __init__(self):
        self.compose_project = None
        self.containers = []
        self.stats = {}
        self.running = True
        self.refresh_rate = 1  # seconds

    def check_docker_running(self):
        """Check if Docker daemon is running"""
        try:
            subprocess.run(["docker", "info"], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE, 
                          check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def find_compose_project(self):
        """Check if current directory contains a docker-compose file"""
        compose_files = [
            "docker-compose.yml",
            "docker-compose.yaml",
            "compose.yml",
            "compose.yaml"
        ]
        
        for file in compose_files:
            if os.path.isfile(file):
                try:
                    with open(file, 'r') as f:
                        compose_config = yaml.safe_load(f)
                    
                    # Get project name from compose file or directory name
                    project_name = compose_config.get('name')
                    if not project_name:
                        project_name = os.path.basename(os.getcwd())
                    
                    self.compose_project = {
                        'name': project_name,
                        'file': file,
                        'services': list(compose_config.get('services', {}).keys())
                    }
                    return True
                except Exception as e:
                    print(f"Error parsing compose file: {e}")
        
        return False

    def get_compose_containers(self):
        """Get containers from the current compose project"""
        try:
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            # Parse the JSON output
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        container = json.loads(line)
                        containers.append(container)
                    except json.JSONDecodeError:
                        pass
            
            self.containers = containers
            return True
        except subprocess.SubprocessError as e:
            return False

    def get_all_containers(self):
        """Get all running containers on the system"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.ID}}\t{{.Names}}\t{{.Image}}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        containers.append({
                            'ID': parts[0],
                            'Name': parts[1],
                            'Image': parts[2]
                        })
            
            self.containers = containers
            return True
        except subprocess.SubprocessError:
            return False

    def get_container_stats(self, container_id):
        """Get stats for a specific container"""
        try:
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}\t{{.PIDs}}", container_id],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            stats_line = result.stdout.strip()
            if stats_line:
                parts = stats_line.split('\t')
                if len(parts) >= 6:
                    return {
                        'cpu_perc': parts[0],
                        'mem_usage': parts[1],
                        'mem_perc': parts[2],
                        'net_io': parts[3],
                        'block_io': parts[4],
                        'pids': parts[5]
                    }
            return None
        except subprocess.SubprocessError:
            return None

    def update_stats(self):
        """Update stats for all containers"""
        new_stats = {}
        for container in self.containers:
            container_id = container.get('ID', container.get('Id', ''))
            if container_id:
                stats = self.get_container_stats(container_id)
                if stats:
                    new_stats[container_id] = stats
        self.stats = new_stats

    def draw_ui(self, stdscr):
        """Draw the TUI using curses"""
        curses.curs_set(0)  # Hide cursor
        curses.start_color()
        curses.use_default_colors()
        
        # Define color pairs
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_YELLOW, -1)
        curses.init_pair(3, curses.COLOR_RED, -1)
        curses.init_pair(4, curses.COLOR_CYAN, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        
        GREEN = curses.color_pair(1)
        YELLOW = curses.color_pair(2)
        RED = curses.color_pair(3)
        CYAN = curses.color_pair(4)
        MAGENTA = curses.color_pair(5)
        
        while self.running:
            try:
                # Get terminal size
                max_y, max_x = stdscr.getmaxyx()
                
                # Clear screen
                stdscr.clear()
                
                # Draw header
                header = "Docker Stats TUI"
                stdscr.addstr(0, (max_x - len(header)) // 2, header, curses.A_BOLD)
                
                # Draw project info if available
                if self.compose_project:
                    project_info = f"Compose Project: {self.compose_project['name']} ({self.compose_project['file']})"
                    stdscr.addstr(1, 0, project_info, CYAN)
                else:
                    stdscr.addstr(1, 0, "System-wide Docker Containers", CYAN)
                
                # Draw current time
                time_str = datetime.now().strftime("%H:%M:%S")
                stdscr.addstr(1, max_x - len(time_str) - 1, time_str)
                
                # Draw column headers
                headers = ["CONTAINER", "CPU %", "MEM USAGE / LIMIT", "MEM %", "NET I/O", "BLOCK I/O", "PIDS"]
                header_y = 3
                
                # Calculate column widths
                container_width = max(20, max_x // 4)
                cpu_width = 8
                mem_usage_width = 20
                mem_perc_width = 8
                net_io_width = 15
                block_io_width = 15
                pids_width = 8
                
                # Draw headers
                stdscr.addstr(header_y, 0, headers[0].ljust(container_width), curses.A_BOLD)
                stdscr.addstr(header_y, container_width, headers[1].ljust(cpu_width), curses.A_BOLD)
                stdscr.addstr(header_y, container_width + cpu_width, headers[2].ljust(mem_usage_width), curses.A_BOLD)
                stdscr.addstr(header_y, container_width + cpu_width + mem_usage_width, headers[3].ljust(mem_perc_width), curses.A_BOLD)
                stdscr.addstr(header_y, container_width + cpu_width + mem_usage_width + mem_perc_width, headers[4].ljust(net_io_width), curses.A_BOLD)
                stdscr.addstr(header_y, container_width + cpu_width + mem_usage_width + mem_perc_width + net_io_width, headers[5].ljust(block_io_width), curses.A_BOLD)
                stdscr.addstr(header_y, container_width + cpu_width + mem_usage_width + mem_perc_width + net_io_width + block_io_width, headers[6], curses.A_BOLD)
                
                # Draw separator
                separator = "-" * (max_x - 1)
                stdscr.addstr(header_y + 1, 0, separator)
                
                # Update container stats
                self.update_stats()
                
                # Draw container stats
                row = header_y + 2
                for container in self.containers:
                    if row >= max_y - 1:
                        break
                    
                    container_id = container.get('ID', container.get('Id', ''))
                    container_name = container.get('Name', container.get('Names', ''))
                    
                    # Truncate container name if too long
                    if len(container_name) > container_width - 3:
                        container_name = container_name[:container_width - 3] + "..."
                    
                    # Draw container name
                    stdscr.addstr(row, 0, container_name.ljust(container_width), MAGENTA)
                    
                    # Draw stats if available
                    if container_id in self.stats:
                        stats = self.stats[container_id]
                        
                        # CPU usage
                        cpu_perc = stats['cpu_perc']
                        cpu_color = GREEN
                        if cpu_perc.endswith('%'):
                            cpu_value = float(cpu_perc[:-1])
                            if cpu_value > 50:
                                cpu_color = YELLOW
                            if cpu_value > 80:
                                cpu_color = RED
                        stdscr.addstr(row, container_width, cpu_perc.ljust(cpu_width), cpu_color)
                        
                        # Memory usage
                        mem_usage = stats['mem_usage']
                        stdscr.addstr(row, container_width + cpu_width, mem_usage.ljust(mem_usage_width))
                        
                        # Memory percentage
                        mem_perc = stats['mem_perc']
                        mem_color = GREEN
                        if mem_perc.endswith('%'):
                            mem_value = float(mem_perc[:-1])
                            if mem_value > 50:
                                mem_color = YELLOW
                            if mem_value > 80:
                                mem_color = RED
                        stdscr.addstr(row, container_width + cpu_width + mem_usage_width, mem_perc.ljust(mem_perc_width), mem_color)
                        
                        # Network I/O
                        net_io = stats['net_io']
                        stdscr.addstr(row, container_width + cpu_width + mem_usage_width + mem_perc_width, net_io.ljust(net_io_width))
                        
                        # Block I/O
                        block_io = stats['block_io']
                        stdscr.addstr(row, container_width + cpu_width + mem_usage_width + mem_perc_width + net_io_width, block_io.ljust(block_io_width))
                        
                        # PIDs
                        pids = stats['pids']
                        stdscr.addstr(row, container_width + cpu_width + mem_usage_width + mem_perc_width + net_io_width + block_io_width, pids)
                    
                    row += 1
                
                # Draw footer
                footer = "Press 'q' to quit, 'r' to refresh"
                stdscr.addstr(max_y - 1, 0, footer)
                
                # Refresh the screen
                stdscr.refresh()
                
                # Handle keyboard input with timeout
                stdscr.timeout(self.refresh_rate * 1000)
                key = stdscr.getch()
                
                if key == ord('q'):
                    self.running = False
                elif key == ord('r'):
                    # Force refresh containers
                    if self.compose_project:
                        self.get_compose_containers()
                    else:
                        self.get_all_containers()
                
                # If no key was pressed, just update the containers periodically
                if key == -1:
                    if self.compose_project:
                        self.get_compose_containers()
                    else:
                        self.get_all_containers()
                
            except curses.error:
                # Handle terminal resize or other curses errors
                pass
            except Exception as e:
                # Exit on other exceptions
                self.running = False
                raise e

    def run(self):
        """Main entry point for the application"""
        # Check if Docker is running
        if not self.check_docker_running():
            print("Error: Docker daemon is not running")
            return 1
        
        # Check for compose project
        if self.find_compose_project():
            print(f"Found Docker Compose project: {self.compose_project['name']}")
            if not self.get_compose_containers():
                print("No running containers in the Compose project. Showing all containers.")
                self.compose_project = None
                self.get_all_containers()
        else:
            print("No Docker Compose project found. Showing all containers.")
            self.get_all_containers()
        
        # Start the TUI
        try:
            curses.wrapper(self.draw_ui)
        except KeyboardInterrupt:
            pass
        
        return 0

if __name__ == "__main__":
    app = DockerStatsTUI()
    sys.exit(app.run())