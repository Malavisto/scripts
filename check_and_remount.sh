#!/bin/bash

# Variables
REMOTE_SHARE="//masungulo/data"
MOUNT_POINT="/mnt/datasmb"
LOG_FILE="/var/log/remount_share.log"
CREDENTIALS="/home/techkid/.smbcredentials"

# Check if the share is mounted
if ! mountpoint -q "$MOUNT_POINT"; then
  echo "$(date): Share is not mounted. Attempting to remount." >> "$LOG_FILE"
  
  # Attempt to remount the share
  mount -t cifs "$REMOTE_SHARE" "$MOUNT_POINT" -o credentials=$CREDENTIALS

  if mountpoint -q "$MOUNT_POINT"; then
    echo "$(date): Successfully remounted the share." >> "$LOG_FILE"
  else
    echo "$(date): Failed to remount the share." >> "$LOG_FILE"
  fi
else
  echo "$(date): Share is already mounted." >> "$LOG_FILE"
fi
