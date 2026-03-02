"""
Debug script to test JWT token authentication for career advisor endpoint.
Run this to verify if your token is valid.
"""

import requests
import json

# Read token from input
print("=" * 60)
print("JWT Token Validator for Career Advisor Endpoint")
print("=" * 60)
print()
print("Instructions:")
print("1. Open your browser console (F12)")
print("2. Run: localStorage.getItem('token')")
print("3. Copy the token value (without quotes)")
print("4. Paste it below")
print()

token_input = input("Enter your token: ").strip()

# Remove quotes if user copied them
if token_input.startswith('"') and token_input.endswith('"'):
    token_input = token_input[1:-1]

# Try to parse as JSON (since it's stored as JSON string)
try:
    token = json.loads(token_input)
    print(f"\n✓ Token parsed from JSON: {token[:50]}...")
except json.JSONDecodeError:
    token = token_input
    print(f"\n✓ Using token as-is: {token[:50]}...")

# Test the token
url = "http://localhost:8000/api/career-advisor/"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}
payload = {}

print(f"\n🔍 Testing endpoint: {url}")
print(f"📤 Authorization header: Bearer {token[:20]}...")
print()

try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    
    print(f"📥 Response Status: {response.status_code}")
    print(f"📥 Response Headers: {dict(response.headers)}")
    print()
    
    if response.status_code == 200:
        print("✅ SUCCESS! Token is valid and endpoint works!")
        print(f"Response: {json.dumps(response.json(), indent=2)[:500]}...")
    elif response.status_code == 401:
        print("❌ AUTHENTICATION FAILED (401)")
        print("Possible reasons:")
        print("  1. Token is expired")
        print("  2. Token format is incorrect")
        print("  3. Token is not a valid JWT")
        print()
        try:
            error_detail = response.json()
            print(f"Error details: {json.dumps(error_detail, indent=2)}")
        except:
            print(f"Raw response: {response.text}")
    else:
        print(f"⚠️  Unexpected status code: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ Request failed: {e}")

print()
print("=" * 60)
