#!/bin/bash

# ------------------------------------------------------------------------------------
# UPS Shutdown Notify Script with Debug Outputs
#
# This script checks the status and battery level of an APC UPS (via NUT),
# sends notifications to Telegram and Discord when relevant changes occur,
# and provides debug information if notifications are not triggered.
#
# Usage:
#   1. Place this script in the same directory as your .env file.
#   2. Update the .env file with TELEGRAM_API_KEY, TELEGRAM_CHAT_ID,
#      DISCORD_WEBHOOK_URL, and UPS_NAME.
#   3. Make this script executable:
#         chmod +x ups_shutdown_notify.sh
#   4. Run the script:
#         ./ups_shutdown_notify.sh
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
if [ -z "$TELEGRAM_API_KEY" ] || [ -z "$TELEGRAM_CHAT_ID" ] || [ -z "$DISCORD_WEBHOOK_URL" ] || [ -z "$UPS_NAME" ] || [ -z "$BATTERY_PERCENT" ]; then
    echo "Error: Missing required environment variables (TELEGRAM_API_KEY, TELEGRAM_CHAT_ID, DISCORD_WEBHOOK_URL, UPS_NAME, BATTERY_PERCENT)."    exit 1
fi

# Configuration
BATTERY_THRESHOLD=$BATTERY_PERCENT
STATE_FILE="$SCRIPT_DIR/ups_state.txt"

# Function to send Telegram notification
send_telegram() {
    local message="$1"
    # -s suppresses curl progress bar, remove -s if you want more curl debug
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_API_KEY/sendMessage" \
        -d chat_id="$TELEGRAM_CHAT_ID" \
        -d text="$message"
}

# Function to send Discord notification
send_discord() {
    local message="$1"
    curl -s -X POST "$DISCORD_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d '{"content":"'"$message"'"}'
}

# Function to send notifications to both platforms and stdout
send_notifications() {
    local message="$1"
    echo "$message"  # Print to stdout
    send_telegram "$message"
    send_discord "$message"
}

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
echo "  Power Status: $ups_status"

# Read previous state from file
previous_status="UNKNOWN"
previous_battery="UNKNOWN"
if [ -f "$STATE_FILE" ]; then
    echo "[DEBUG] Loading previous state from $STATE_FILE"
    # shellcheck disable=SC1090
    . "$STATE_FILE"
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