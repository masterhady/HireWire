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
    # print(f"Raw: {data}") 

    matched_user = data.get('data', {}).get('matchedUser')
    if not matched_user:
        print("User not found")
        return

    calendar_str = matched_user.get('submissionCalendar', '{}')
    calendar = json.loads(calendar_str)
    
    print(f"Stats for {username}:")
    print(f"Total Calendar Entries: {len(calendar)}")
    
    # Calculate submissions for December 2024
    target_month = 12
    target_year = 2024
    
    total_submissions_in_month = 0
    for timestamp, count in calendar.items():
        dt = datetime.datetime.fromtimestamp(int(timestamp))
        if dt.month == target_month and dt.year == target_year:
            total_submissions_in_month += count
            
    print(f"Submissions in {target_month}/{target_year}: {total_submissions_in_month}")

get_leetcode_calendar("qiyuangong") 
