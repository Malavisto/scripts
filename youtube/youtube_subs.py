from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import datetime
import json
import os

# Disable OAuthlib's HTTPS verification when running locally.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Updated scopes to include channel selection
SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

class QuotaTracker:
    def __init__(self):
        self.subscription_requests = 0
        
    def add_subscription_request(self):
        self.subscription_requests += 1
        
    def get_total_units(self):
        return self.subscription_requests
        
    def print_summary(self):
        total_units = self.get_total_units()
        print(f"\nAPI Usage Summary:")
        print(f"- Subscription requests made: {self.subscription_requests}")
        print(f"- Total quota units used: {total_units}/10,000 daily free quota")
        print(f"- Remaining free quota: {10000 - total_units} units")

def get_authenticated_service():
    """Get authenticated YouTube service."""
    try:
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets.json', 
                SCOPES,
                redirect_uri='http://localhost:8080'
            )
            creds = flow.run_local_server(port=8080)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        return build('youtube', 'v3', credentials=creds)
    except FileNotFoundError:
        print("\nError: client_secrets.json file not found!")
        print("Please make sure you have downloaded your OAuth 2.0 credentials")
        print("from Google Cloud Console and saved them as 'client_secrets.json'")
        raise

def get_channel_id(youtube):
    """Get all channels accessible to the authenticated user."""
    try:
        channels_response = youtube.channels().list(
            part='snippet',
            mine=True
        ).execute()

        # Print available channels for selection
        print("\nAvailable channels:")
        for i, channel in enumerate(channels_response['items'], 1):
            print(f"{i}. {channel['snippet']['title']}")

        # Let user select channel
        while True:
            try:
                choice = int(input("\nSelect your channel number: ")) - 1
                if 0 <= choice < len(channels_response['items']):
                    return channels_response['items'][choice]['id']
                print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a number.")
    except Exception as e:
        print(f"Error getting channels: {e}")
        raise

def get_subscriptions(youtube, channel_id, quota_tracker):
    """Fetch all subscriptions for specified channel."""
    all_subscriptions = []
    next_page_token = None
    
    try:
        while True:
            request = youtube.subscriptions().list(
                part='snippet',
                channelId=channel_id,
                maxResults=50,
                pageToken=next_page_token
            )
            
            quota_tracker.add_subscription_request()
            response = request.execute()
            
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
                break
            
    except KeyboardInterrupt:
        print("\nFetching interrupted by user. Saving partial results...")
        return all_subscriptions
    except Exception as e:
        print(f"\nError fetching subscriptions: {e}")
        if all_subscriptions:
            print("Saving partial results...")
            return all_subscriptions
        raise
    
    return all_subscriptions

def main():
    quota_tracker = QuotaTracker()
    
    try:
        print("Authenticating...")
        youtube = get_authenticated_service()
        
        # Get channel ID for brand account
        channel_id = get_channel_id(youtube)
        
        print("\nFetching subscriptions...")
        print("(Press Ctrl+C at any time to stop and save partial results)")
        subs = get_subscriptions(youtube, channel_id, quota_tracker)
        
        if not subs:
            print("No subscriptions were fetched. Exiting...")
            return
        
        print("\nSorting results...")
        subs.sort(key=lambda x: x['subscribed_at'])
        
        print("Saving to file...")
        with open('my_subscriptions.json', 'w', encoding='utf-8') as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)
        
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
        print("\nScript stopped by user")
        if 'subs' in locals() and subs:
            print("Saving partial results...")
            with open('my_subscriptions.json', 'w', encoding='utf-8') as f:
                json.dump(subs, f, ensure_ascii=False, indent=2)
            print(f"Saved {len(subs)} subscriptions to 'my_subscriptions.json'")
            quota_tracker.print_summary()
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == '__main__':
    main()