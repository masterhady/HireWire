#!/usr/bin/env python3
"""
Test the career advisor endpoint with the actual token from the browser.
"""

import requests
import json

# The exact token from the browser
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY1NjYxNjQ0LCJpYXQiOjE3NjU2NTgwNDQsImp0aSI6IjQ0YjI0ZDgwMDJkYTQ2MTNhMmM0MzU5OTVkMjQ2MjgxIiwidXNlcl9pZCI6MTA1LCJyb2xlIjoiam9ic2Vla2VyIiwidXNlcm5hbWUiOiJ0ZXN0ZXJAdGVzdGVSNC5jb20ifQ.K1SAC86ryzT5UZFQ0PUl4H5I23l-EBTbqXMysTV-LQU"

url = "http://localhost:8000/api/career-advisor/"
headers = {
    "Authorization": "Bearer " + TOKEN,
    "Content-Type": "application/json",
}
payload = {}

print("=" * 70)
print("Testing Career Advisor Endpoint")
print("=" * 70)
print(f"\nURL: {url}")
print(f"Authorization: Bearer {TOKEN[:50]}...")
print(f"\nMaking POST request...")

try:
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    
    print(f"\n{'='*70}")
    print(f"Response Status: {response.status_code}")
    print(f"{'='*70}")
    
    if response.status_code == 200:
        print("\n✅ SUCCESS!")
        data = response.json()
        print(f"\nResponse data:")
        print(json.dumps(data, indent=2)[:1000])
    else:
        print(f"\n❌ ERROR: {response.status_code}")
        print(f"\nResponse Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        print(f"\nResponse Body:")
        try:
            error_data = response.json()
            print(json.dumps(error_data, indent=2))
        except:
            print(response.text)
            
except Exception as e:
    print(f"\n❌ Request failed with exception:")
    print(f"  {type(e).__name__}: {e}")

print(f"\n{'='*70}")
