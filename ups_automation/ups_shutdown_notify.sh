#!/bin/bash
set -euo pipefail

# ------------------------------------------------------------------------------------
# UPS Shutdown Notify Script with Internet-Aware Notification
#
# This script checks the status and battery level of an APC UPS (via NUT),
# sends (or queues) notifications to Telegram and Discord when relevant changes occur,
# and provides debug information if notifications are not triggered.
#
# Usage:
#   1. Place this script in the same directory as your .env file.
#   2. Update the .env file with TELEGRAM_API_KEY, TELEGRAM_CHAT_ID,
#      DISCORD_WEBHOOK_URL, UPS_NAME, and BATTERY_PERCENT.
#   3. Make this script executable:
#         chmod +x ups_shutdown_notify.sh
#   4. Run the script:
#         ./ups_shutdown_notify.sh
#
# If there's no internet connection, the notification is queued locally; notifications
# will be resent the next time the script runs and detects an internet connection.
# ------------------------------------------------------------------------------------

# Get script directory for relative .env path
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Load environment variables from .env in script directory
ENV_FILE="$SCRIPT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    echo "[DEBUG] Loading .env from: $ENV_FILE"
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "Error: .env file not found in $SCRIPT_DIR"
    exit 1
fi

# Validate required environment variables
if [ -z "${TELEGRAM_API_KEY:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ] \
   || [ -z "${DISCORD_WEBHOOK_URL:-}" ] || [ -z "${UPS_NAME:-}" ] || [ -z "${BATTERY_PERCENT:-}" ]; then
    echo "Error: Missing required environment variables (TELEGRAM_API_KEY, TELEGRAM_CHAT_ID, DISCORD_WEBHOOK_URL, UPS_NAME, BATTERY_PERCENT)."
    exit 1
fi

# Configuration
BATTERY_THRESHOLD="$BATTERY_PERCENT"
STATE_FILE="$SCRIPT_DIR/ups_state.txt"
PENDING_NOTIFICATIONS_FILE="$SCRIPT_DIR/pending_notifications.txt"

# Function to check internet connectivity
has_internet() {
    # Try pinging a reliable host
    ping -c 1 8.8.8.8 &>/dev/null
}

# Function to send Telegram notification
send_telegram() {
    local message="$1"
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_API_KEY/sendMessage" \
        -d chat_id="$TELEGRAM_CHAT_ID" \
        -d text="$message"
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to send Telegram notification"
    fi
}

# Function to send Discord notification
send_discord() {
    local message="$1"
    curl -s -X POST "$DISCORD_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d '{"content":"'"$message"'"}'
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to send Discord notification"
    fi
}

# Function to actually send them if internet is available,
# or queue them if not.
send_notification_internet_aware() {
    local message="$1"

    if has_internet; then
        # Internet is available, send notifications now
        echo "[DEBUG] Internet is available. Sending notifications."
        send_telegram "$message"
        send_discord "$message"
    else
        # Internet is NOT available, write to queue
        echo "[DEBUG] No internet. Queueing notification."
        echo "$message" >> "$PENDING_NOTIFICATIONS_FILE"
    fi
}

process_queued_notifications() {
    if [ -f "$PENDING_NOTIFICATIONS_FILE" ] && has_internet; then
        echo "[DEBUG] Internet is available. Sending queued notifications."
        while IFS= read -r queued_message; do
            send_telegram "$queued_message"
            send_discord "$queued_message"
        done < "$PENDING_NOTIFICATIONS_FILE"
        # Clear the file after sending
        > "$PENDING_NOTIFICATIONS_FILE"
    fi
}

# Function to send notifications to both platforms and stdout
send_notifications() {
    local message="$1"
    echo "$message"  # Print to stdout
    send_notification_internet_aware "$message"
}

# Process any pending notifications from previous runs
process_queued_notifications

# Retrieve UPS status information
echo "[DEBUG] Retrieving UPS status for: $UPS_NAME"
battery_status=$(upsc "$UPS_NAME" 2>/dev/null | grep "battery.charge" | awk '{print $2}')
ups_status=$(upsc "$UPS_NAME" 2>/dev/null | grep "ups.status" | awk '{print $2}')

# If upsc commands fail, these variables might be empty
if [ -z "$battery_status" ] || [ -z "$ups_status" ]; then
    echo "Error: Could not retrieve UPS information. Check UPS_NAME or NUT configuration."
    echo "[DEBUG] battery_status='$battery_status' ups_status='$ups_status'"
    exit 1
fi

# Output current status
echo "Current UPS Status:"
echo "  Battery Level: $battery_status%"
echo "  Power Status:  $ups_status"

# Read previous state from file
previous_status="UNKNOWN"
previous_battery="UNKNOWN"
if [ -f "$STATE_FILE" ]; then
    echo "[DEBUG] Loading previous state from $STATE_FILE"
    if [ -r "$STATE_FILE" ]; then
        # shellcheck disable=SC1090
        . "$STATE_FILE"
    else
        echo "[ERROR] State file is not readable. Exiting..."
        exit 1
    fi
else
    echo "[DEBUG] No previous state file found; using defaults."
fi

echo "[DEBUG] Previous: status='$previous_status', battery='$previous_battery%'"
echo "[DEBUG] Current:  status='$ups_status', battery='$battery_status%'"

# Check if UPS status changed from Online (OL) to On Battery (OB) or vice versa
if [ "$ups_status" = "OB" ] && [ "$previous_status" != "OB" ]; then
    send_notifications "⚡ UPS has switched to battery power!"
elif [ "$ups_status" = "OL" ] && [ "$previous_status" = "OB" ]; then
    send_notifications "✅ Power has been restored. UPS is back on main power."
else
    echo "[DEBUG] No OB/OL status change detected."
fi

# Check if battery level became critical
if [ "$battery_status" -le "$BATTERY_THRESHOLD" ] && [ "$previous_battery" -gt "$BATTERY_THRESHOLD" ]; then
    send_notifications "🔋 Battery level at threshold ($battery_status%). Initiating shutdown..."
    /usr/sbin/shutdown +0
else
    echo "[DEBUG] Battery not in critical threshold or no change from previous."
fi

# Save current state
{
    echo "previous_status='$ups_status'"
    echo "previous_battery='$battery_status'"
} > "$STATE_FILE"
echo "[DEBUG] State saved to $STATE_FILE"

# Show changes in stdout
if [ "$previous_status" != "$ups_status" ]; then
    echo "Status changed from $previous_status to $ups_status"
fi

if [ "$previous_battery" != "$battery_status" ]; then
    echo "Battery level changed from $previous_battery% to $battery_status%"
fi

echo "[DEBUG] Script complete."