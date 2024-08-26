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

# Upload both the message and the log file to Discord
curl -X POST "$WEBHOOK_URL" \
     -F "file=@$TEMP_MESSAGE_FILE" \
     -F "file=@$LOGFILE"