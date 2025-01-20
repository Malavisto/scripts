#!/bin/bash

# Deployment script for server maintenance automation
# This script downloads and sets up the server maintenance script and its environment

# Prevent script from running partially if curl fails
set -e

# If not running with sudo, rerun with sudo
if [ "$(id -u)" != "0" ]; then
    echo "This script must be run as root. Attempting to use sudo..."
    exec sudo "$0" "$@"
fi

# Detect if script is being piped from curl
if [ -t 1 ]; then
    # Running normally
    PIPED=0
else
    # Being piped
    PIPED=1
fi

# Default values
GITHUB_RAW_URL="https://raw.githubusercontent.com/Malavisto/scripts/refs/heads/main/maintainence/server-maintenance.sh"
DEFAULT_INSTALL_DIR="/opt/server-maintenance"

# Colors for output (only if not piped)
if [ $PIPED -eq 0 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# Function to print colored messages
print_message() {
    local color=$1
    local message=$2
    printf "${color}%s${NC}\n" "$message"
}

# Function to check if a command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_message "$RED" "Error: $1 is required but not installed."
        exit 1
    fi
}

# Check required commands
check_command "curl"
check_command "chmod"

# Welcome message
print_message "$GREEN" "Server Maintenance Script Deployment"
print_message "$GREEN" "======================================"

# Get installation directory from user with proper variable handling
INSTALL_DIR=""
while [ -z "$INSTALL_DIR" ]; do
    read -p "Enter installation directory [$DEFAULT_INSTALL_DIR]: " INSTALL_DIR_INPUT
    INSTALL_DIR=${INSTALL_DIR_INPUT:-$DEFAULT_INSTALL_DIR}
    
    # Validate the directory path
    if [[ ! "$INSTALL_DIR" =~ ^/ ]]; then
        print_message "$RED" "Error: Please provide an absolute path (starting with /)."
        INSTALL_DIR=""
    fi
done

# Create installation directory with error handling
if [ ! -d "$INSTALL_DIR" ]; then
    print_message "$YELLOW" "Creating directory: $INSTALL_DIR"
    if ! sudo mkdir -p "$INSTALL_DIR"; then
        print_message "$RED" "Error: Failed to create directory $INSTALL_DIR"
        exit 1
    fi
fi

# Download the maintenance script with error handling
print_message "$GREEN" "Downloading maintenance script..."
if ! sudo curl -s -o "$INSTALL_DIR/server-maintenance.sh" "$GITHUB_RAW_URL"; then
    print_message "$RED" "Error: Failed to download the script from $GITHUB_RAW_URL"
    exit 1
fi

# Set correct permissions
sudo chmod 755 "$INSTALL_DIR/server-maintenance.sh"

# Create .env file
print_message "$GREEN" "Setting up .env file..."
if [ ! -f "$INSTALL_DIR/.env" ]; then
    # Get Discord webhook URL from user with validation
    DISCORD_WEBHOOK=""
    while [ -z "$DISCORD_WEBHOOK" ]; do
        read -p "Enter Discord webhook URL: " DISCORD_WEBHOOK
        if [ -z "$DISCORD_WEBHOOK" ]; then
            print_message "$RED" "Discord webhook URL cannot be empty."
        fi
    done
    
    # Create .env file with restricted permissions
    if ! sudo bash -c "cat > '$INSTALL_DIR/.env'" << EOL
# Environment variables for server maintenance script
DISCORD_WEBHOOK="$DISCORD_WEBHOOK"
EOL
    then
        print_message "$RED" "Error: Failed to create .env file"
        exit 1
    fi
    
    sudo chmod 600 "$INSTALL_DIR/.env"
    print_message "$GREEN" ".env file created successfully"
else
    print_message "$YELLOW" ".env file already exists, skipping creation"
fi

# Set up cron job
print_message "$GREEN" "Would you like to set up a cron job for automated maintenance?"
read -p "Run maintenance daily at 3 AM? (y/n): " SETUP_CRON

if [[ $SETUP_CRON =~ ^[Yy]$ ]]; then
    # Create cron job
    CRON_CMD="0 3 * * * $INSTALL_DIR/server-maintenance.sh >> /var/log/server-maintenance.log 2>&1"
    
    # Add to root's crontab with error handling
    if ! (sudo crontab -l 2>/dev/null | grep -v "server-maintenance.sh"; echo "$CRON_CMD") | sudo crontab -; then
        print_message "$RED" "Failed to set up cron job"
        exit 1
    fi
    print_message "$GREEN" "Cron job set up successfully"
fi

# Final setup verification
if [ -f "$INSTALL_DIR/server-maintenance.sh" ] && [ -f "$INSTALL_DIR/.env" ]; then
    print_message "$GREEN" "
========================================
Installation completed successfully!

Installation Directory: $INSTALL_DIR
Maintenance Script: $INSTALL_DIR/server-maintenance.sh
Environment File: $INSTALL_DIR/.env

You can run the maintenance script manually with:
sudo $INSTALL_DIR/server-maintenance.sh
========================================"
else
    print_message "$RED" "Installation may have completed with errors. Please check the output above."
fi
