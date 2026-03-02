import requests
import json
import datetime

def get_leetcode_calendar(username):
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
        
        print(f"Status: {response.status_code}")
        data = response.json()
        
        if 'errors' in data:
            print(f"Errors: {data['errors']}")
            return

        matched_user = data.get('data', {}).get('matchedUser')
        if not matched_user:
            print("User not found or matchedUser is null")
            return

        calendar_str = matched_user.get('submissionCalendar', '{}')
        calendar = json.loads(calendar_str)
        
        print(f"Stats for {username}:")
        print(f"Total Calendar Entries: {len(calendar)}")
        
        # Calculate submissions for 2024 (any month)
        submissions_by_month = {}
        for timestamp, count in calendar.items():
            dt = datetime.datetime.fromtimestamp(int(timestamp))
            if dt.year == 2024:
                month = dt.month
                submissions_by_month[month] = submissions_by_month.get(month, 0) + count
                
        print(f"Submissions in 2024 by month: {submissions_by_month}")

    except Exception as e:
        print(f"Exception: {e}")

get_leetcode_calendar("awice") 
