import requests
import json
import datetime

def verify_user(username):
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

        # 1. Analyze Total Solved
        submit_stats = matched_user.get('submitStats', {}).get('acSubmissionNum', [])
        total_solved = 0
        total_accepted_submissions = 0
        for stat in submit_stats:
            if stat['difficulty'] == 'All':
                total_solved = stat['count']
                total_accepted_submissions = stat['submissions']
                break
        
        print(f"Total Unique Solved: {total_solved}")
        print(f"Total Accepted Submissions: {total_accepted_submissions}")

        # 2. Analyze Submission Calendar
        calendar_str = matched_user.get('submissionCalendar', '{}')
        submission_calendar = json.loads(calendar_str)
        
        total_calendar_submissions = sum(submission_calendar.values())
        print(f"Total Submissions in Calendar: {total_calendar_submissions}")
        
        # Calculate for December 2024
        dec_2024_count = 0
        for ts, val in submission_calendar.items():
            dt = datetime.datetime.fromtimestamp(int(ts))
            if dt.month == 12 and dt.year == 2024:
                dec_2024_count += val
                
        print(f"Submissions in Dec 2024: {dec_2024_count}")
        
        # Check if all activity is in Dec 2024
        is_all_dec = total_calendar_submissions == dec_2024_count
        print(f"Is all activity in Dec 2024? {is_all_dec}")

    except Exception as e:
        print(f"Error: {e}")

verify_user("abody_ali2")
