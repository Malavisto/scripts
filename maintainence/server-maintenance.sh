#!/bin/bash

# Server Maintenance Script
# This script performs common maintenance tasks on Ubuntu servers
# Recommended to run as a daily/weekly cron job

# Configuration
LOG_FILE="/var/log/server-maintenance.log"
DISCORD_WEBHOOK="YOUR_DISCORD_WEBHOOK_URL"  # Replace with your Discord webhook URL

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to send Discord notification
send_discord_notification() {
    local message="$1"
    curl -H "Content-Type: application/json" \
         -X POST \
         -d "{\"content\":\"$message\"}" \
         "$DISCORD_WEBHOOK"
}

# Check if running as root
if [ "$(id -u)" != "0" ]; then
    log_message "Error: This script must be run as root"
    exit 1
fi

# Start maintenance
log_message "Starting server maintenance"
send_discord_notification "🔧 Starting server maintenance on $(hostname)"

# Update package list and upgrade packages
log_message "Updating package list and upgrading packages"
apt-get update >> "$LOG_FILE" 2>&1
apt-get -y upgrade >> "$LOG_FILE" 2>&1

# Check if reboot is required
RESTART_REQUIRED=false
if [ -f /var/run/reboot-required ]; then
    RESTART_REQUIRED=true
    PACKAGES_REQUIRING_RESTART=$(cat /var/run/reboot-required.pkgs)
    send_discord_notification "🔄 **Restart Required**: System restart needed on $(hostname)\n\nPackages requiring restart:\n\`\`\`$PACKAGES_REQUIRING_RESTART\`\`\`"
fi

# Additional check for kernel updates
CURRENT_KERNEL=$(uname -r)
LATEST_KERNEL=$(ls -t /boot/vmlinuz-* | head -n1 | sed 's/\/boot\/vmlinuz-//')
if [ "$CURRENT_KERNEL" != "$LATEST_KERNEL" ]; then
    RESTART_REQUIRED=true
    send_discord_notification "🔄 **Kernel Update**: New kernel version available ($LATEST_KERNEL). Current kernel: $CURRENT_KERNEL. System restart recommended on $(hostname)"
fi

# Check for services that need restart
SERVICES_TO_RESTART=$(needrestart -b 2>/dev/null | grep "NEEDRESTART-SVC" || true)
if [ -n "$SERVICES_TO_RESTART" ]; then
    send_discord_notification "🔄 **Services Need Restart**: The following services need to be restarted on $(hostname):\n\`\`\`$SERVICES_TO_RESTART\`\`\`"
fi

# Remove unused packages and clean package cache
log_message "Cleaning up unused packages and cache"
apt-get -y autoremove >> "$LOG_FILE" 2>&1
apt-get -y autoclean >> "$LOG_FILE" 2>&1
apt-get -y clean >> "$LOG_FILE" 2>&1

# Clean journal logs older than 7 days
log_message "Cleaning old journal logs"
journalctl --vacuum-time=7d >> "$LOG_FILE" 2>&1

# Clean old log files
find /var/log -type f -name "*.log.*" -mtime +30 -delete
find /var/log -type f -name "*.gz" -mtime +30 -delete

# Check disk space
log_message "Checking disk space"
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    send_discord_notification "⚠️ **Warning**: Disk usage is at ${DISK_USAGE}% on $(hostname)"
fi

# Check system memory
log_message "Checking memory usage"
MEM_USAGE=$(free | awk '/Mem:/ {printf("%.2f"), $3/$2 * 100}')
if [ "$(echo "$MEM_USAGE > 90" | bc)" -eq 1 ]; then
    send_discord_notification "⚠️ **Warning**: Memory usage is at ${MEM_USAGE}% on $(hostname)"
fi

# Check for failed systemd services
log_message "Checking for failed services"
FAILED_SERVICES=$(systemctl --failed)
if [ -n "$FAILED_SERVICES" ]; then
    send_discord_notification "🚨 **Alert**: Failed services detected on $(hostname):\n\`\`\`$FAILED_SERVICES\`\`\`"
fi

# Monitor system load
log_message "Current system load:"
SYSTEM_LOAD=$(uptime | awk '{print $10}' | cut -d',' -f1)
if [ "$(echo "$SYSTEM_LOAD > 4" | bc)" -eq 1 ]; then
    send_discord_notification "⚠️ **Warning**: High system load (${SYSTEM_LOAD}) detected on $(hostname)"
fi

# Check available updates
UPDATES=$(apt list --upgradable 2>/dev/null | grep -c upgradable)
SECURITY_UPDATES=$(apt list --upgradable 2>/dev/null | grep -i security | wc -l)

# Send update notification to Discord
if [ $SECURITY_UPDATES -gt 0 ]; then
    send_discord_notification "🔒 **Security Alert**: ${SECURITY_UPDATES} security updates available on $(hostname)"
fi

# Create system statistics summary
{
    echo "System Statistics Summary"
    echo "------------------------"
    echo "Disk Usage: ${DISK_USAGE}%"
    echo "Memory Usage: ${MEM_USAGE}%"
    echo "System Load: ${SYSTEM_LOAD}"
    echo "Updates Available: $UPDATES"
    echo "Security Updates Available: $SECURITY_UPDATES"
    echo "Restart Required: $RESTART_REQUIRED"
} > /var/log/system_stats.txt

# Maintenance complete
log_message "Maintenance complete"
send_discord_notification "✅ Server maintenance completed on $(hostname)"
