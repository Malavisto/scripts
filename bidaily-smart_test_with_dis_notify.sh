#!/bin/bash

#Config
source ./config.env
WEBHOOK_URL="$DISCORD_WEBHOOK_URL"
DRIVE="/dev/sda"
LOGFILE="/var/log/smart_test_result.log"

# Get hostname and system time
HOSTNAME=$(hostname)
SYSTEM_TIME=$(date)

# Run a short SMART test
smartctl -t short "$DRIVE"

# Wait for the test to complete
sleep 180  # 3 minutes; adjust based on the test type (short or long)

# Log the results
smartctl -a "$DRIVE" > "$LOGFILE"

# Send a text message to Discord
curl -X POST "$WEBHOOK_URL" \
     -H "Content-Type: application/json" \
     -d "{\"content\": \"SMART log of $HOSTNAME at $SYSTEM_TIME:\"}"

# Upload the log file to Discord
curl -X POST "$WEBHOOK_URL" \
     -F "file=@$LOGFILE"

echo "SMART test results and message uploaded to Discord"