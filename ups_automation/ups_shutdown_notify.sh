#!/bin/bash

# Get environment variables
TELEGRAM_API_KEY=$TELEGRAM_API_KEY
TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID
DISCORD_WEBHOOK_URL=$DISCORD_WEBHOOK_URL

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

# Check UPS battery status
battery_status=$(upsc $UPS_NAME | grep "battery.charge" | awk '{print $2}')
ups_status=$(upsc $UPS_NAME | grep "ups.status" | awk '{print $2}')

# Notify if UPS goes on battery
if [ "$ups_status" == "OB" ]; then
    send_telegram "UPS is running on battery power."
    send_discord "UPS is running on battery power."
fi

# Check battery level
if [ "$battery_status" -le "$BATTERY_THRESHOLD" ]; then
    send_telegram "Battery level critical ($battery_status%). Shutting down the server."
    send_discord "Battery level critical ($battery_status%). Shutting down the server."
    # Trigger shutdown
    /sbin/shutdown -h now
fi
