#!/bin/bash

# Get environment variables
TELEGRAM_API_KEY=$TELEGRAM_API_KEY
TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID
DISCORD_WEBHOOK_URL=$DISCORD_WEBHOOK_URL
UPS_NAME=$UPS_NAME
BATTERY_THRESHOLD=20 
STATE_FILE="/tmp/ups_state.txt"

# Function to send Telegram notification
send_telegram() {
    local message="$1"
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

# Function to send notifications to both platforms
send_notifications() {
    local message="$1"
    send_telegram "$message"
    send_discord "$message"
}
# Check UPS battery status
battery_status=$(upsc $UPS_NAME | grep "battery.charge" | awk '{print $2}')
ups_status=$(upsc $UPS_NAME | grep "ups.status" | awk '{print $2}')

# Read previous state
previous_status="UNKNOWN"
previous_battery="UNKNOWN"
if [ -f "$STATE_FILE" ]; then
    . "$STATE_FILE"
fi

# Check if UPS status changed
if [ "$ups_status" == "OB" ] && [ "$previous_status" != "OB" ]; then
    send_notifications "⚡ UPS has switched to battery power!"
elif [ "$ups_status" == "OL" ] && [ "$previous_status" == "OB" ]; then
    send_notifications "✅ Power has been restored. UPS is back on main power."
fi

# Check if battery level became critical
if [ "$battery_status" -le "$BATTERY_THRESHOLD" ] && [ "$previous_battery" -gt "$BATTERY_THRESHOLD" ]; then
    send_notifications "🔋 Battery level critical ($battery_status%). Initiating shutdown..."
    /sbin/shutdown -h now
fi

# Save current state
echo "previous_status='$ups_status'" > "$STATE_FILE"
echo "previous_battery='$battery_status'" >> "$STATE_FILE"
