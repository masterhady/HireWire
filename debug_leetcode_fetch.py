import sys
import os
import django
import logging

# Set up Django environment
sys.path.append('/home/iti/Documents/AI_Project_MVP/core')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Configure logging to see errors
logging.basicConfig(level=logging.DEBUG)

from api.services.leetcode_service import LeetCodeService

def test_fetch():
    username = "abody_ali2" # Using the username from previous context if available, or a known one
    print(f"Attempting to fetch stats for {username}...")
    
    try:
        stats = LeetCodeService.get_user_stats(username, target_role="Mid-Level")
        if stats:
            print("Successfully fetched stats!")
            print(f"Total Solved: {stats.get('total_solved')}")
            print(f"Problem Solving Score: {stats.get('problem_solving_score')}")
        else:
            print("Failed to fetch stats (returned None).")
    except Exception as e:
        print(f"Exception occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fetch()
