#!/bin/bash

#Config
source ./config.env
WEBHOOK_URL="$DISCORD_WEBHOOK_URL"
DRIVE="/dev/sda"
LOGFILE="/var/log/smart_test_result.log"
TEMP_MESSAGE_FILE="/tmp/smart_log_message.txt"


# Run a short SMART test
smartctl -t short "$DRIVE"

# Wait for the test to complete
sleep 180  # 3 minutes; adjust based on the test type (short or long)

# Log the results
smartctl -a "$DRIVE" > "$LOGFILE"

# Upload both the message and the log file to Discord
curl -X POST "$WEBHOOK_URL" \
     -F "file=@$TEMP_MESSAGE_FILE" \
     -F "file=@$LOGFILE"

# Clean up temporary files
rm "$TEMP_MESSAGE_FILE"     