import json
import csv
import datetime
from pathlib import Path

def format_date(date_str):
    """Convert ISO date string to a more readable format."""
    try:
        date = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        return date.strftime("%B %d, %Y")
    except:
        return date_str

def create_csv(input_file='my_subscriptions.json', output_file='subscriptions.csv'):
    """Convert JSON data to CSV format."""
    try:
        # Read JSON file
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            print("No data found in JSON file.")
            return
        
        # Sort data by subscription date
        data.sort(key=lambda x: x['subscribed_at'])
        
        # Prepare CSV fields
        fieldnames = [
            'Channel Name',
            'Channel ID',
            'Subscription Date',
            'Days Subscribed',
            'URL'
        ]
        
        # Calculate days subscribed
        current_date = datetime.datetime.now()
        
        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in data:
                sub_date = datetime.datetime.strptime(item['subscribed_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
                days_subscribed = (current_date - sub_date).days
                
                writer.writerow({
                    'Channel Name': item['channel_name'],
                    'Channel ID': item['channel_id'],
                    'Subscription Date': format_date(item['subscribed_at']),
                    'Days Subscribed': days_subscribed,
                    'URL': f"https://youtube.com/channel/{item['channel_id']}"
                })
        
        print(f"CSV file created successfully: {output_file}")
        print(f"Total subscriptions: {len(data)}")
        
    except FileNotFoundError:
        print(f"Error: Could not find input file '{input_file}'")
    except Exception as e:
        print(f"Error creating CSV: {str(e)}")

def create_pretty_json(input_file='my_subscriptions.json', output_file='subscriptions_pretty.json'):
    """Create a more readable JSON file with additional information."""
    try:
        # Read JSON file
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            print("No data found in JSON file.")
            return
        
        # Sort data by subscription date
        data.sort(key=lambda x: x['subscribed_at'])
        
        # Create enhanced data structure
        enhanced_data = {
            "metadata": {
                "total_subscriptions": len(data),
                "export_date": datetime.datetime.now().strftime("%B %d, %Y %H:%M:%S"),
                "oldest_subscription": format_date(data[0]['subscribed_at']),
                "newest_subscription": format_date(data[-1]['subscribed_at'])
            },
            "subscriptions": [
                {
                    "channel_name": item['channel_name'],
                    "channel_id": item['channel_id'],
                    "subscription_date": format_date(item['subscribed_at']),
                    "channel_url": f"https://youtube.com/channel/{item['channel_id']}",
                    "days_subscribed": (datetime.datetime.now() - 
                                      datetime.datetime.strptime(item['subscribed_at'], 
                                                              "%Y-%m-%dT%H:%M:%S.%fZ")).days
                }
                for item in data
            ]
        }
        
        # Write pretty JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_data, f, indent=4, ensure_ascii=False)
        
        print(f"Pretty JSON file created successfully: {output_file}")
        print(f"Total subscriptions: {len(data)}")
        
    except FileNotFoundError:
        print(f"Error: Could not find input file '{input_file}'")
    except Exception as e:
        print(f"Error creating pretty JSON: {str(e)}")

def main():
    print("YouTube Subscriptions Data Formatter")
    print("====================================")
    
    while True:
        print("\nWhat would you like to do?")
        print("1. Create CSV file")
        print("2. Create pretty JSON file")
        print("3. Create both")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == '1':
            create_csv()
        elif choice == '2':
            create_pretty_json()
        elif choice == '3':
            create_csv()
            create_pretty_json()
        elif choice == '4':
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()