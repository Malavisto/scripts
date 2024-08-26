#!/bin/bash

#Collect Variables
source ./config.env

# Specify the hard drive you want to test
DRIVE="/dev/sda"  # Replace /dev/sdX with your actual drive (e.g., /dev/sda)

# Run a short SMART test
smartctl -t short "$DRIVE"

# Wait for the test to complete
sleep 300  # 5 minutes; adjust based on the test type (short or long)

# Log the results
LOGFILE="/var/log/smart_test_result.log"
smartctl -a "$DRIVE" > "$LOGFILE"

# Upload the log file to Discord
WEBHOOK_URL="$DISCORD_WEBHOOK_URL"

curl -X POST "$WEBHOOK_URL" \
     -F "file=@$LOGFILE"
