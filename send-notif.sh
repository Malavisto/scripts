#!/bin/bash


DRIVE="/dev/sda"

# Get hostname and system time
HOSTNAME=$(hostname)
SYSTEM_TIME=$(date)



#Collect Variables
source ./config.env

# Log the results
LOGFILE="/var/log/smart_test_result.log"
smartctl -a "$DRIVE" > "$LOGFILE"
chmod +rwx "$LOGFILE"


WEBHOOK_URL="$DISCORD_WEBHOOK_URL"

# Send a text message to Discord
curl -X POST "$WEBHOOK_URL" \
     -H "Content-Type: application/json" \
     -d "{\"content\": \"SMART log of $HOSTNAME at $SYSTEM_TIME:\"}"

# Upload the log file to Discord
curl -X POST "$WEBHOOK_URL" \
     -F "file=@$LOGFILE"

echo "SMART test results and message uploaded to Discord"     