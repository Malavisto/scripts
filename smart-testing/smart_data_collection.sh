#!/bin/bash

# Set variables
DRIVE="/dev/sda"
OUTPUT_FILE="/tmp/smart_results.txt"

# Function to collect SMART data
collect_smart_data() {
    smartctl -a $DRIVE > $OUTPUT_FILE
}

# Main execution
if ! command -v smartctl &> /dev/null; then
    echo "smartctl could not be found. Please install smartmontools."
    exit 1
fi

if [ ! -b "$DRIVE" ]; then
    echo "Drive $DRIVE does not exist."
    exit 1
fi

collect_smart_data

echo "SMART data collected and saved to $OUTPUT_FILE"
