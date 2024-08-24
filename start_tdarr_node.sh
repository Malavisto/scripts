#!/bin/bash

# Path to the Tdarr node executable
TDARR_NODE_PATH="/home/techkid/Tdarr_Updater/Tdarr_Node/Tdarr_Node"

# Name of the tmux session
TMUX_SESSION_NAME="tdarr_node"

# Check if the Tdarr node executable exists
if [ -f "$TDARR_NODE_PATH" ]; then
    # Start a new tmux session and run the Tdarr node executable within it
    tmux new-session -d -s $TMUX_SESSION_NAME "$TDARR_NODE_PATH"
    echo "Tdarr node started in tmux session '$TMUX_SESSION_NAME'."
else
    echo "Tdarr node executable not found at $TDARR_NODE_PATH."
fi