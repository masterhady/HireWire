# 🔑 How to Get JWT Token

## Quick Steps

### **1. Start Your Django Server**
```bash
cd /home/mariem/HireWire
source venv/bin/activate
python manage.py runserver
```

Server should be running on `http://localhost:8000`

---

### **2. Login via API to Get JWT Token**

**Method 1: Using cURL**
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "your-password"
  }'
```

**Method 2: Using Postman**

```
POST http://localhost:8000/api/auth/login/
Content-Type: application/json

{
  "email": "your-email@example.com",
  "password": "your-password"
}
```

---

### **3. Copy the Access Token**

**Example Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjQ4MjM0NTY3LCJpYXQiOjE2NDgyMzA5NjcsImp0aSI6IjEyMzQ1Njc4IiwidXNlcl9pZCI6MSwiZW1haWwiOiJ1c2VyQGV4YW1wbGUuY29tIn0.xyz123...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Copy the `access` value** - this is your JWT token!

---

### **4. Use the Token**

**In the HTML test page:**
1. Paste the token in "Enter JWT Token" field
2. Now you can load questions

**In API calls:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

---

### **5. If You Don't Have an Account**

**Register first:**
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "first_name": "Test",
    "last_name": "User"
  }'
```

Then login with those credentials.

---

## 🎯 Quick Test

**Test your token:**
```bash
curl -X GET http://localhost:8000/api/audio-interview/history/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE"
```

If you see your interview history → Token is valid! ✅

---

## 💡 Token Expiration

- Access token expires in ~15 minutes
- If you get 401 errors, get a new token
- Refresh token can be used to get new access token

**Refresh Token:**
```bash
POST http://localhost:8000/api/auth/token/refresh/
Body: { "refresh": "your_refresh_token" }
```

---

Copy the `access` token from the login response and paste it into the HTML test page! 🎉
