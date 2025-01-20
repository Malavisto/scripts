# Server Maintenance Script

Automated server maintenance script for Ubuntu servers that performs common maintenance tasks and sends notifications to Discord.

## Features

- System updates and package management
- Disk space monitoring
- Memory usage monitoring
- Service health checks
- Kernel update detection
- Security updates monitoring
- System statistics reporting
- Discord notifications
- Automated log cleanup

## Quick Installation

Deploy the maintenance script with a single command:

```bash
curl -sSL https://raw.githubusercontent.com/Malavisto/scripts/refs/heads/main/maintainence/deployment-script.sh | sudo bash
```

This will:
1. Download the deployment script
2. Create the installation directory
3. Set up the maintenance script
4. Configure the environment file
5. Set appropriate permissions
6. Optionally configure a daily cron job

## Manual Installation

If you prefer to inspect the script before running it, you can:

1. Download the deployment script:
```bash
curl -O https://raw.githubusercontent.com/Malavisto/scripts/refs/heads/main/maintainence/deployment-script.sh
```

2. Review the script content:
```bash
less deployment-script.sh
```

3. Make it executable and run:
```bash
chmod +x deployment-script.sh
sudo ./deployment-script.sh
```

## Configuration

The script will prompt you for:
- Installation directory (default: /opt/server-maintenance)
- Discord webhook URL for notifications
- Cron job setup preference

## Security Considerations

- The deployment script runs with sudo privileges
- The .env file permissions are set to 600 (readable only by root)
- The maintenance script permissions are set to 755
- All operations are logged for accountability

## Requirements

- Ubuntu/Debian-based system (probably works on other linux systems)
- Root/sudo access
- curl installed
- Discord webhook URL for notifications

## Logs

- Main log file: `/var/log/server-maintenance.log`
- System statistics: `/var/log/system_stats.txt`

## Manual Usage

After installation, you can manually run the maintenance script:

```bash
sudo /opt/server-maintenance/server-maintenance.sh
```

## Uninstallation

To remove the maintenance script and its configuration:

```bash
sudo rm -rf /opt/server-maintenance
```

Don't forget to remove the cron job if you set one up:

```bash
sudo crontab -l | grep -v "server-maintenance.sh" | sudo crontab -
```

## Contributing

Feel free to open issues or submit pull requests with improvements.

## License

[MIT License](https://github.com/Malavisto/scripts/blob/main/LICENSE)
