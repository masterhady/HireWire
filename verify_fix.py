import requests
import json
import datetime

def verify_leetcode_service(username):
    # Simulate the backend service call
    query = """
    query getUserProfile($username: String!) {
        matchedUser(username: $username) {
            username
            submissionCalendar
            submitStats: submitStatsGlobal {
                acSubmissionNum {
                    difficulty
                    count
                    submissions
                }
            }
        }
    }
    """
    variables = {"username": username}
    
    try:
        response = requests.post(
            "https://leetcode.com/graphql",
            json={'query': query, 'variables': variables},
            headers={
                'Content-Type': 'application/json',
                'Referer': 'https://leetcode.com',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            timeout=15
        )
        
        data = response.json()
        matched_user = data.get('data', {}).get('matchedUser')
        
        if not matched_user:
            print("User not found")
            return

        calendar_str = matched_user.get('submissionCalendar', '{}')
        submission_calendar = json.loads(calendar_str)
        
        print(f"Successfully fetched submissionCalendar for {username}")
        print(f"Total entries: {len(submission_calendar)}")
        
        # Simulate frontend logic
        target_month = 12
        target_year = 2024
        count = 0
        
        for ts, val in submission_calendar.items():
            dt = datetime.datetime.fromtimestamp(int(ts))
            if dt.month == target_month and dt.year == target_year:
                count += val
                
        print(f"Calculated submissions for {target_month}/{target_year}: {count}")
        
    except Exception as e:
        print(f"Error: {e}")

verify_leetcode_service("awice")
