from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import datetime
import json
import os
import logging
from logging.handlers import RotatingFileHandler

# Disable OAuthlib's HTTPS verification when running locally.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Updated scopes to include channel selection
SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

def setup_logging():
    """Configure logging settings."""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logger
    logger = logging.getLogger('YouTubeSubscriptions')
    logger.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Create file handler
    file_handler = RotatingFileHandler(
        'logs/youtube_subs.log',
        maxBytes=1024*1024,  # 1MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

class QuotaTracker:
    def __init__(self, logger):
        self.subscription_requests = 0
        self.logger = logger
        
    def add_subscription_request(self):
        self.subscription_requests += 1
        self.logger.debug(f"API request made. Total requests: {self.subscription_requests}")
        
    def get_total_units(self):
        return self.subscription_requests
        
    def print_summary(self):
        total_units = self.get_total_units()
        summary = (
            f"\nAPI Usage Summary:\n"
            f"- Subscription requests made: {self.subscription_requests}\n"
            f"- Total quota units used: {total_units}/10,000 daily free quota\n"
            f"- Remaining free quota: {10000 - total_units} units"
        )
        self.logger.info(summary)
        print(summary)

def get_authenticated_service(logger):
    """Get authenticated YouTube service."""
    try:
        logger.info("Starting authentication process")
        if os.path.exists('token.json'):
            logger.debug("Found existing token.json")
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        else:
            logger.info("No token.json found. Starting OAuth flow")
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets.json', 
                SCOPES,
                redirect_uri='http://localhost:8080'
            )
            creds = flow.run_local_server(port=8080)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            logger.info("Authentication successful. Token saved")
        
        return build('youtube', 'v3', credentials=creds)
    except FileNotFoundError:
        logger.error("client_secrets.json file not found!")
        print("\nError: client_secrets.json file not found!")
        print("Please make sure you have downloaded your OAuth 2.0 credentials")
        print("from Google Cloud Console and saved them as 'client_secrets.json'")
        raise

def get_channel_id(youtube, logger):
    """Get all channels accessible to the authenticated user."""
    try:
        logger.info("Fetching available channels")
        channels_response = youtube.channels().list(
            part='snippet',
            mine=True
        ).execute()

        print("\nAvailable channels:")
        for i, channel in enumerate(channels_response['items'], 1):
            channel_name = channel['snippet']['title']
            print(f"{i}. {channel_name}")
            logger.debug(f"Found channel: {channel_name}")

        while True:
            try:
                choice = int(input("\nSelect your channel number: ")) - 1
                if 0 <= choice < len(channels_response['items']):
                    selected_channel = channels_response['items'][choice]['snippet']['title']
                    logger.info(f"Selected channel: {selected_channel}")
                    return channels_response['items'][choice]['id']
                logger.warning("Invalid channel selection")
                print("Invalid choice. Please try again.")
            except ValueError:
                logger.warning("Invalid input: not a number")
                print("Please enter a number.")
    except Exception as e:
        logger.error(f"Error getting channels: {str(e)}")
        raise

def get_subscriptions(youtube, channel_id, quota_tracker, logger):
    """Fetch all subscriptions for specified channel."""
    all_subscriptions = []
    next_page_token = None
    
    try:
        logger.info("Starting subscription fetch")
        while True:
            request = youtube.subscriptions().list(
                part='snippet',
                channelId=channel_id,
                maxResults=50,
                pageToken=next_page_token
            )
            
            quota_tracker.add_subscription_request()
            response = request.execute()
            
            batch_size = len(response['items'])
            logger.debug(f"Fetched batch of {batch_size} subscriptions")
            
            for item in response['items']:
                sub_info = {
                    'channel_name': item['snippet']['title'],
                    'channel_id': item['snippet']['resourceId']['channelId'],
                    'subscribed_at': item['snippet']['publishedAt']
                }
                all_subscriptions.append(sub_info)
            
            print(f"Fetched {len(all_subscriptions)} subscriptions so far...", end='\r')
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                logger.info(f"Completed fetch. Total subscriptions: {len(all_subscriptions)}")
                break
            
    except KeyboardInterrupt:
        logger.warning("Fetch interrupted by user")
        print("\nFetching interrupted by user. Saving partial results...")
        return all_subscriptions
    except Exception as e:
        logger.error(f"Error fetching subscriptions: {str(e)}")
        print(f"\nError fetching subscriptions: {e}")
        if all_subscriptions:
            logger.info("Saving partial results due to error")
            print("Saving partial results...")
            return all_subscriptions
        raise
    
    return all_subscriptions

def main():
    logger = setup_logging()
    quota_tracker = QuotaTracker(logger)
    
    try:
        logger.info("Starting YouTube Subscriptions Export")
        print("Authenticating...")
        youtube = get_authenticated_service(logger)
        
        channel_id = get_channel_id(youtube, logger)
        
        print("\nFetching subscriptions...")
        print("(Press Ctrl+C at any time to stop and save partial results)")
        subs = get_subscriptions(youtube, channel_id, quota_tracker, logger)
        
        if not subs:
            logger.warning("No subscriptions fetched")
            print("No subscriptions were fetched. Exiting...")
            return
        
        logger.info("Processing and saving results")
        print("\nSorting results...")
        subs.sort(key=lambda x: x['subscribed_at'])
        
        print("Saving to file...")
        with open('my_subscriptions.json', 'w', encoding='utf-8') as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Successfully saved {len(subs)} subscriptions")
        print(f"\nSuccessfully saved {len(subs)} subscriptions!")
        
        print("\nYour 5 most recent subscriptions:")
        for sub in subs[-5:]:
            sub_date = datetime.datetime.strptime(
                sub['subscribed_at'], 
                "%Y-%m-%dT%H:%M:%SZ"
            ).strftime('%Y-%m-%d')
            print(f"- {sub['channel_name']} (subscribed on {sub_date})")
        
        print("\nAll subscriptions have been saved to 'my_subscriptions.json'")
        quota_tracker.print_summary()
        
    except KeyboardInterrupt:
        logger.warning("Script interrupted by user")
        print("\nScript stopped by user")
        if 'subs' in locals() and subs:
            logger.info("Saving partial results due to interruption")
            print("Saving partial results...")
            with open('my_subscriptions.json', 'w', encoding='utf-8') as f:
                json.dump(subs, f, ensure_ascii=False, indent=2)
            print(f"Saved {len(subs)} subscriptions to 'my_subscriptions.json'")
            quota_tracker.print_summary()
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        print(f"\nAn error occurred: {e}")

if __name__ == '__main__':
    main()