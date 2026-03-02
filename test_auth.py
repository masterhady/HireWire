"""
Simple test to verify JWT authentication is working properly.
This will make a test request to the career advisor endpoint.
"""

import sys

# Test 1: Try to import required modules
print("Testing imports...")
try:
    import requests
    print("✓ requests module available")
except ImportError:
    print("✗ requests module not available")
    print("Install with: pip install requests")
    sys.exit(1)

# Test 2: Check if Django server is running
print("\nTesting Django server...")
try:
    response = requests.get("http://localhost:8000/api/test-supabase/", timeout=5)
    print(f"✓ Django server is running (status: {response.status_code})")
except requests.exceptions.ConnectionError:
    print("✗ Django server is not running or not accessible")
    print("Start with: python manage.py runserver")
    sys.exit(1)
except Exception as e:
    print(f"⚠ Unexpected error: {e}")

# Test 3: Try to login and get a token
print("\nTesting login endpoint...")
login_url = "http://localhost:8000/api/auth/login/"
test_credentials = {
    "username": input("Enter your username: ").strip(),
    "password": input("Enter your password: ").strip()
}

try:
    response = requests.post(login_url, json=test_credentials, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access")
        print(f"✓ Login successful!")
        print(f"✓ Token received: {token[:50]}...")
        
        # Test 4: Use the token to access career advisor
        print("\nTesting career advisor endpoint with token...")
        career_url = "http://localhost:8000/api/career-advisor/"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        career_response = requests.post(career_url, headers=headers, json={}, timeout=30)
        
        print(f"Status Code: {career_response.status_code}")
        
        if career_response.status_code == 200:
            print("✅ SUCCESS! Career advisor endpoint works with this token!")
        elif career_response.status_code == 401:
            print("❌ AUTHENTICATION FAILED (401)")
            print("Response:", career_response.text[:500])
        elif career_response.status_code == 404:
            print("❌ User has no CV uploaded")
            print("Response:", career_response.json())
        else:
            print(f"⚠ Unexpected status: {career_response.status_code}")
            print("Response:", career_response.text[:500])
            
    else:
        print(f"✗ Login failed (status: {response.status_code})")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"✗ Error: {e}")
