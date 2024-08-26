#!/bin/bash

#Collect Variables
source ./config.env

# Log the results
LOGFILE="/var/log/smart_test_result.log"
smartctl -a "$DRIVE" > "$LOGFILE"
chmod +rwx "$LOGFILE"

# Upload the log file to Discord
WEBHOOK_URL="$DISCORD_WEBHOOK_URL"

curl -X POST "$WEBHOOK_URL" \
     -F "file=@$LOGFILE"

