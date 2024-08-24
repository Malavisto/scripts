#!/bin/bash

# Path to the Tdarr node executable
TDARR_NODE_PATH="/home/techkid/Tdarr_Updater/Tdarr_Node/Tdarr_Node"
# Check if the Tdarr node executable exists
if [ -f "$TDARR_NODE_PATH" ]; then
    # Run the Tdarr node executable
    "$TDARR_NODE_PATH" &
    echo "Tdarr node started successfully."
else
    echo "Tdarr node executable not found at $TDARR_NODE_PATH."
fi
