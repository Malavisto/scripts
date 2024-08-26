#Collect Variables
source ./config.env

# Log the results
LOGFILE="/var/log/smart_test_result.log"
smartctl -a "$DRIVE" > "$LOGFILE"

# Send Discord notification
WEBHOOK_URL="$DISCORD_WEBHOOK_URL"
MESSAGE="SMART Test Results:\n$(cat $LOGFILE)"
curl -H "Content-Type: application/json" -X POST -d "{\"content\": \"$MESSAGE\"}" "$WEBHOOK_URL"
