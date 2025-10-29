# 🔧 Audio Interview Setup Instructions

## ⚠️ Issue: Invalid OpenAI API Key

The OpenAI API key in your `.env` file is either:
- Expired or revoked
- Incorrect or corrupted
- Not activated yet

**Error**: `401 - Incorrect API key provided`

---

## ✅ Solution: Get a New OpenAI API Key

### **Step 1: Get Your API Key**
1. Go to https://platform.openai.com/account/api-keys
2. Sign in with your OpenAI account
3. Click **"Create new secret key"**
4. Copy the new key (it starts with `sk-...`)

### **Step 2: Add to .env File**
```bash
# Edit your .env file
cd /home/mariem/HireWire
nano .env  # or use your preferred editor

# Add this line (replace with your actual key):
OPENAI_API_KEY=sk-your-actual-key-here
```

### **Step 3: Restart the Server**
```bash
# Stop the current server (if running)
pkill -f "python manage.py runserver"

# Start it again
cd /home/mariem/HireWire
source venv/bin/activate
python manage.py runserver
```

### **Step 4: Generate Audio for Existing Questions**
```bash
# Run the audio generation script
source venv/bin/activate
python generate_missing_audio.py
```

---

## 🎯 Quick Testing Commands

Once your API key is set up correctly:

### **1. Generate New Audio Interview Questions**
```bash
POST http://localhost:8000/api/audio-interview/questions/
Headers:
  Authorization: Bearer YOUR_JWT_TOKEN
  Content-Type: application/json

Body:
{
  "job_description": "Senior Full Stack Developer...",
  "question_count": 3,
  "voice_id": "alloy",
  "difficulty": "medium"
}
```

### **2. Play Question Audio**
```bash
GET http://localhost:8000/api/audio-interview/question/{question_id}/audio/
Headers:
  Authorization: Bearer YOUR_JWT_TOKEN
```

---

## 📝 Alternative: Test Without Audio

If you want to test the audio interview feature WITHOUT OpenAI:

1. **Skip TTS** - Questions will work but won't have audio files
2. **Skip STT** - You can still submit audio but won't get automatic transcription
3. **Manual Transcription** - Users can manually provide text

The system gracefully handles missing audio (as you've already experienced with the "No audio file available" message).

---

## 🔍 Troubleshooting

### **Key Not Loading?**
```bash
# Check if key is in .env
grep OPENAI_API_KEY .env

# Verify it's being loaded
python manage.py shell -c "from decouple import config; print(bool(config('OPENAI_API_KEY')))"
```

### **Key Still Invalid?**
- Make sure there are no extra spaces in the .env file
- Make sure the key starts with `sk-`
- Check if your OpenAI account has available credits
- Try generating a new key if the problem persists

---

## 🎤 Once Working

After fixing the API key, you'll be able to:

✅ Generate questions with TTS audio  
✅ Play question audio in the browser/app  
✅ Record audio answers  
✅ Get automatic STT transcription  
✅ Receive comprehensive AI evaluation  

Happy testing! 🎉
