#!/bin/bash

# Configuration - MODIFY THESE VALUES
# Uncomment HOME if you want to backup a specific user's home directory or script is ran as root
#HOME="/home/user"                           # Home directory to backup
BACKUP_DIR="/path/to/backup/location"        # Example: /mnt/backup or /home/user/backups
DISCORD_WEBHOOK_URL="YOUR_WEBHOOK_URL_HERE"  # Get this from Discord channel settings
MAX_BACKUPS=2

# Home directory exclusions - Add or remove as needed
EXCLUDES=(
    "$HOME/Downloads"
    "$HOME/Music"
    "$HOME/Videos"
    "$HOME/Pictures"
    "$HOME/.cache"
    "$HOME/snap"
    "$HOME/.local/share/Trash"
)

# Function to send Discord notifications
send_discord_notification() {
    local message="$1"
    local color="$2"  # Optional: Hex color for embed
    
    # Default to green if no color specified
    [[ -z "$color" ]] && color="65280"

    # Create a JSON payload with an embed
    local payload=$(cat <<EOF
{
  "embeds": [{
    "title": "Backup Status",
    "description": "$message",
    "color": $color,
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  }]
}
EOF
)

    # Send to Discord
    curl -H "Content-Type: application/json" \
         -d "$payload" \
         "$DISCORD_WEBHOOK_URL" 2>/dev/null
}

# Function to rotate backups
rotate_backups() {
    local prefix=$1
    # List backups from oldest to newest
    local backups=($(ls -t ${BACKUP_DIR}/${prefix}_*.tar.gz 2>/dev/null))
    
    # Remove old backups if we have more than MAX_BACKUPS
    while [ ${#backups[@]} -ge $MAX_BACKUPS ]; do
        echo "Removing old backup: ${backups[-1]}"
        rm "${backups[-1]}"
        backups=(${backups[@]::${#backups[@]}-1})
    done
}

# Function to log messages with timestamps
log_message() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message"
}

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Start backup process
DATE=$(date +%Y%m%d)
send_discord_notification "🚀 Starting backup process..." "16776960"  # Yellow

# Prepare exclude arguments for tar
EXCLUDE_ARGS=""
for exclude in "${EXCLUDES[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude=$exclude"
done

# Backup home directory
log_message "Starting home directory backup..."
tar -czf "$BACKUP_DIR/home_${DATE}.tar.gz" $EXCLUDE_ARGS -C $HOME .

if [ $? -eq 0 ]; then
    log_message "Home directory backup completed successfully"
    rotate_backups "home"
else
    log_message "Error: Home directory backup failed"
    send_discord_notification "❌ Home directory backup failed!" "16711680"  # Red
    exit 1
fi

# Backup Docker volumes
log_message "Starting Docker volumes backup..."
docker run --rm \
    -v /var/lib/docker/volumes:/volumes:ro \
    -v "$BACKUP_DIR":/backup \
    ubuntu tar czf "/backup/docker_volumes_${DATE}.tar.gz" /volumes

if [ $? -eq 0 ]; then
    log_message "Docker volumes backup completed successfully"
    rotate_backups "docker_volumes"
else
    log_message "Error: Docker volumes backup failed"
    send_discord_notification "❌ Docker volumes backup failed!" "16711680"  # Red
    exit 1
fi

# Calculate total size of current backups
total_size=$(du -sh "$BACKUP_DIR" | cut -f1)

# Get list of current backups
backup_list=$(ls -lh "$BACKUP_DIR" | awk '{print "• "$9" ("$5")"}' | grep -v '^• total')

# Send success notification with details
success_message=$(cat <<EOF
✅ Backup completed successfully!

📦 Total backup size: $total_size

Current backups:
$backup_list
EOF
)

send_discord_notification "$success_message" "65280"  # Green

log_message "Backup completed. Total backup size: $total_size"
