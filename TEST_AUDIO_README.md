# 🧪 Audio Interview HTML Test Page

## 📝 How to Use

### **Step 1: Get a Question ID**
Generate audio interview questions first (using Postman or API):

```bash
POST http://localhost:8000/api/audio-interview/questions/
Authorization: Bearer YOUR_JWT_TOKEN
Body: {
  "job_description": "Senior Full Stack Developer...",
  "question_count": 1
}
```

Copy a `question_id` from the response.

---

### **Step 2: Get JWT Token**
Login to get your token:

```bash
POST http://localhost:8000/api/auth/login/
Body: {
  "email": "your-email@example.com",
  "password": "your-password"
}
```

Copy the `access` token.

---

### **Step 3: Open Test Page**
```bash
# In browser, open:
file:///home/mariem/HireWire/test_audio.html

# OR if running a local server:
http://localhost:8000/test_audio.html
```

---

### **Step 4: Fill in the Form**

1. **Enter JWT Token** (from Step 2)
2. **Enter Question ID** (from Step 1)
3. Click **"Load Question"** → Question appears
4. Click **"Speak Question"** → Hear the question via TTS
5. Click **"Start Recording"** → Speak your answer
6. Click **"Stop & Get Transcription"** → Get transcribed text
7. Click **"Submit Answer"** → Send to API

---

### **Step 5: View Results**
Results appear at the bottom with full API response.

---

## 🎯 What This Tests

✅ **Browser TTS** - Text-to-speech for questions  
✅ **Browser STT** - Speech-to-text for answers  
✅ **Audio Recording** - MediaRecorder API  
✅ **API Integration** - Full submission flow  
✅ **Fireworks AI** - No OpenAI needed!

---

## 🚨 Browser Requirements

### **Chrome/Edge** ✅
- Full support for TTS and STT
- MediaRecorder support

### **Firefox** ⚠️
- TTS works
- STT may not work (use manual text input)

### **Safari** ⚠️
- Limited support
- Try Chrome/Edge for best results

---

## 💡 Tips

1. **Allow Microphone Permission** when prompted
2. **Speak Clearly** for best transcription
3. **Check Transcribed Text** before submitting
4. **Use Chrome/Edge** for best compatibility

---

## 📊 Expected Flow

```
1. Load Question → GET question text ✅
2. Speak Question → Browser TTS plays audio 🔊
3. Record Answer → Browser records audio 🎙️
4. Live Transcription → Speech recognition types your words 📝
5. Submit Answer → Send to API with audio + text 📤
6. View Results → See API response with answer ID 🎉
```

---

That's it! Happy testing! 🎤✨
