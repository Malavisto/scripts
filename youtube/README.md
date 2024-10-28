# YouTube Subscriptions Manager

This project provides two Python scripts that help you manage and format your YouTube subscription data. With these scripts, you can authenticate with YouTube, fetch your subscription list, and save it in JSON or CSV format with a readable structure.

## Requirements
1. **Python 3.x**
2. **Google API Client Libraries**: You can install the required packages using:
    ```bash
    pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
    ```
3. **YouTube Data API Key**: You'll need a `client_secrets.json` file containing your OAuth 2.0 credentials from [Google Cloud Console](https://console.cloud.google.com/).

### Setting Up `client_secrets.json`
1. Visit the [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. Enable the YouTube Data API v3 for your project.
3. Set up OAuth 2.0 credentials, download the `client_secrets.json` file, and place it in the same directory as the scripts.

## Scripts Overview

### 1. `youtube_subs.py`

This script authenticates with YouTube, retrieves all subscriptions for a selected channel, and saves them in `my_subscriptions.json`.

- **Usage**: Run the script with:
    ```bash
    python youtube_subs.py
    ```
- **Functions**:
  - **Authentication**: Logs you in to your YouTube account using OAuth 2.0.
  - **Channel Selection**: Lists available channels and lets you select which one to retrieve subscriptions from.
  - **Data Retrieval**: Fetches and saves subscription data (channel name, ID, and subscription date).

- **Output**: `my_subscriptions.json`, containing all your YouTube subscriptions in JSON format.

### 2. `format_subscriptions.py`

This script reads the `my_subscriptions.json` file, formats the subscription data, and outputs it as a CSV file (`subscriptions.csv`) and/or a more readable JSON file (`subscriptions_pretty.json`).

- **Usage**: Run the script with:
    ```bash
    python format_subscriptions.py
    ```
  You can choose to create a CSV file, a formatted JSON file, or both.

- **Functions**:
  - **Date Formatting**: Converts the subscription date to a more readable format.
  - **CSV and JSON Output**:
    - **CSV Output** (`subscriptions.csv`): Lists each subscription along with the channel URL, days subscribed, and formatted subscription date.
    - **Formatted JSON Output** (`subscriptions_pretty.json`): Provides metadata, such as total subscriptions and oldest/newest subscription dates.

## Example
1. Run `youtube_subs.py` to fetch your subscriptions and save them to `my_subscriptions.json`.
2. Run `format_subscriptions.py` to create well-formatted CSV and JSON files for easy reading.

## Error Handling
If an error occurs due to a date format mismatch, ensure the format includes microseconds (`%Y-%m-%dT%H:%M:%S.%fZ`) to match the date data in `my_subscriptions.json`.

## License
This project is licensed under the MIT License.
