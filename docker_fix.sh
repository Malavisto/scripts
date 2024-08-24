#!/bin/bash
# Disable AppArmor restriction for unprivileged user namespaces
sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0

#Wait 10 secs before restarting Docker
sleep 10

# Function to check if Docker Desktop is active
is_docker_active() {
  systemctl --user is-active --quiet docker-desktop
}

# Check Docker Desktop status
if is_docker_active; then
  echo "Docker Desktop is running."
else
  echo "Docker Desktop is not running. Applying fix..."

  # Restart Docker Desktop
  if systemctl --user restart docker-desktop; then
  echo "Docker Desktop restarted successfully."
  else
    echo "Failed to restart Docker Desktop." >&2
    exit 1
  fi
fi
