#!/usr/bin/env python3
"""
Docker Stats TUI - A terminal-based UI for monitoring Docker container stats
"""

import os
import sys
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
        # Minimum column widths to ensure readability
        self.min_widths = {
            "container": 10,
            "cpu": 6,
            "mem_usage": 12,
            "mem_perc": 6,
            "net_io": 10,
            "block_io": 10,
            "pids": 5
        }

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
        
    def calculate_column_widths(self, max_x):
        """Calculate column widths based on terminal width"""
        # Total available space minus borders/padding
        available_width = max_x - 7  # Account for some spacing between columns
        
        # Calculate container name width (dynamically sized, gets extra space)
        # First, allocate minimum space for the fixed-width columns
        fixed_width_total = sum([
            self.min_widths["cpu"],
            self.min_widths["mem_usage"],
            self.min_widths["mem_perc"],
            self.min_widths["net_io"],
            self.min_widths["block_io"],
            self.min_widths["pids"]
        ])
        
        # Container column gets the remaining space, but at least its minimum width
        container_width = max(self.min_widths["container"], available_width - fixed_width_total)
        
        # If terminal is very narrow, distribute the available space proportionally
        if available_width < fixed_width_total + self.min_widths["container"]:
            # Calculate proportional distribution
            total_min = sum(self.min_widths.values())
            container_width = max(2, int(available_width * self.min_widths["container"] / total_min))
            cpu_width = max(2, int(available_width * self.min_widths["cpu"] / total_min))
            mem_usage_width = max(2, int(available_width * self.min_widths["mem_usage"] / total_min))
            mem_perc_width = max(2, int(available_width * self.min_widths["mem_perc"] / total_min))
            net_io_width = max(2, int(available_width * self.min_widths["net_io"] / total_min))
            block_io_width = max(2, int(available_width * self.min_widths["block_io"] / total_min))
            pids_width = max(2, int(available_width * self.min_widths["pids"] / total_min))
        else:
            # Normal distribution with minimum widths
            cpu_width = self.min_widths["cpu"]
            mem_usage_width = self.min_widths["mem_usage"]
            mem_perc_width = self.min_widths["mem_perc"]
            net_io_width = self.min_widths["net_io"]
            block_io_width = self.min_widths["block_io"]
            pids_width = self.min_widths["pids"]
        
        return {
            "container": container_width,
            "cpu": cpu_width,
            "mem_usage": mem_usage_width,
            "mem_perc": mem_perc_width,
            "net_io": net_io_width,
            "block_io": block_io_width,
            "pids": pids_width
        }
    
    def truncate_text(self, text, max_width):
        """Truncate text if it's longer than max_width"""
        if len(text) > max_width - 3 and max_width > 3:
            return text[:max_width - 3] + "..."
        return text[:max_width]

    def draw_ui(self, stdscr):
        """Draw the TUI using curses"""
        curses.curs_set(0)  # Hide cursor
        curses.start_color()
        curses.use_default_colors()
        
        # Enable handling of window resize
        stdscr.nodelay(1)
        
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
                
                # Calculate column widths based on terminal size
                widths = self.calculate_column_widths(max_x)
                
                # Clear screen
                stdscr.clear()
                
                # Draw header
                header = "Docker Stats TUI"
                stdscr.addstr(0, max(0, (max_x - len(header)) // 2), header, curses.A_BOLD)
                
                # Draw project info if available
                if self.compose_project:
                    project_info = f"Compose Project: {self.compose_project['name']} ({self.compose_project['file']})"
                    project_info = self.truncate_text(project_info, max_x - 1)
                    stdscr.addstr(1, 0, project_info, CYAN)
                else:
                    info_text = "System-wide Docker Containers"
                    stdscr.addstr(1, 0, info_text, CYAN)
                
                # Draw current time
                time_str = datetime.now().strftime("%H:%M:%S")
                if max_x > len(time_str) + 1:
                    stdscr.addstr(1, max_x - len(time_str) - 1, time_str)
                
                # Draw column headers
                headers = ["CONTAINER", "CPU %", "MEM USAGE / LIMIT", "MEM %", "NET I/O", "BLOCK I/O", "PIDS"]
                header_y = 3
                
                # Position tracking for columns
                x_pos = 0
                
                # Draw headers according to calculated widths
                stdscr.addstr(header_y, x_pos, self.truncate_text(headers[0], widths["container"]), curses.A_BOLD)
                x_pos += widths["container"] + 1
                
                if x_pos < max_x:
                    stdscr.addstr(header_y, x_pos, self.truncate_text(headers[1], widths["cpu"]), curses.A_BOLD)
                    x_pos += widths["cpu"] + 1
                
                if x_pos < max_x:
                    stdscr.addstr(header_y, x_pos, self.truncate_text(headers[2], widths["mem_usage"]), curses.A_BOLD)
                    x_pos += widths["mem_usage"] + 1
                
                if x_pos < max_x:
                    stdscr.addstr(header_y, x_pos, self.truncate_text(headers[3], widths["mem_perc"]), curses.A_BOLD)
                    x_pos += widths["mem_perc"] + 1
                
                if x_pos < max_x:
                    stdscr.addstr(header_y, x_pos, self.truncate_text(headers[4], widths["net_io"]), curses.A_BOLD)
                    x_pos += widths["net_io"] + 1
                
                if x_pos < max_x:
                    stdscr.addstr(header_y, x_pos, self.truncate_text(headers[5], widths["block_io"]), curses.A_BOLD)
                    x_pos += widths["block_io"] + 1
                
                if x_pos < max_x:
                    stdscr.addstr(header_y, x_pos, self.truncate_text(headers[6], widths["pids"]), curses.A_BOLD)
                
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
                    
                    # Truncate container name
                    container_name = self.truncate_text(container_name, widths["container"])
                    
                    # Column position tracking
                    x_pos = 0
                    
                    # Draw container name
                    stdscr.addstr(row, x_pos, container_name, MAGENTA)
                    x_pos += widths["container"] + 1
                    
                    # Draw stats if available and if terminal is wide enough
                    if container_id in self.stats and x_pos < max_x:
                        stats = self.stats[container_id]
                        
                        # CPU usage
                        if x_pos < max_x:
                            cpu_perc = stats['cpu_perc']
                            cpu_color = GREEN
                            if cpu_perc.endswith('%'):
                                cpu_value = float(cpu_perc[:-1])
                                if cpu_value > 50:
                                    cpu_color = YELLOW
                                if cpu_value > 80:
                                    cpu_color = RED
                            cpu_perc = self.truncate_text(cpu_perc, widths["cpu"])
                            stdscr.addstr(row, x_pos, cpu_perc, cpu_color)
                            x_pos += widths["cpu"] + 1
                        
                        # Memory usage
                        if x_pos < max_x:
                            mem_usage = self.truncate_text(stats['mem_usage'], widths["mem_usage"])
                            stdscr.addstr(row, x_pos, mem_usage)
                            x_pos += widths["mem_usage"] + 1
                        
                        # Memory percentage
                        if x_pos < max_x:
                            mem_perc = stats['mem_perc']
                            mem_color = GREEN
                            if mem_perc.endswith('%'):
                                mem_value = float(mem_perc[:-1])
                                if mem_value > 50:
                                    mem_color = YELLOW
                                if mem_value > 80:
                                    mem_color = RED
                            mem_perc = self.truncate_text(mem_perc, widths["mem_perc"])
                            stdscr.addstr(row, x_pos, mem_perc, mem_color)
                            x_pos += widths["mem_perc"] + 1
                        
                        # Network I/O
                        if x_pos < max_x:
                            net_io = self.truncate_text(stats['net_io'], widths["net_io"])
                            stdscr.addstr(row, x_pos, net_io)
                            x_pos += widths["net_io"] + 1
                        
                        # Block I/O
                        if x_pos < max_x:
                            block_io = self.truncate_text(stats['block_io'], widths["block_io"])
                            stdscr.addstr(row, x_pos, block_io)
                            x_pos += widths["block_io"] + 1
                        
                        # PIDs
                        if x_pos < max_x:
                            pids = self.truncate_text(stats['pids'], widths["pids"])
                            stdscr.addstr(row, x_pos, pids)
                    
                    row += 1
                
                # Draw footer if there's room
                if max_y > 4:
                    footer = "Press 'q' to quit, 'r' to refresh"
                    footer = self.truncate_text(footer, max_x - 1)
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
                elif key == curses.KEY_RESIZE:
                    # Just let the loop redraw everything with new dimensions
                    stdscr.clear()
                
                # If no key was pressed, just update the containers periodically
                if key == -1:
                    if self.compose_project:
                        self.get_compose_containers()
                    else:
                        self.get_all_containers()
                
            except curses.error as e:
                # Clear and continue on curses errors
                stdscr.clear()
                continue
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
