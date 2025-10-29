# 🧪 Audio Interview Testing Guide

## 📋 Quick Test Steps

### **1. Start Your Server**
```bash
cd /home/mariem/HireWire
source venv/bin/activate
python manage.py runserver
```

The server should start on `http://localhost:8000`

---

### **2. Get JWT Token (Login)**

**POST** `http://localhost:8000/api/auth/login/`

**Body:**
```json
{
  "email": "your-email@example.com",
  "password": "your-password"
}
```

**Save the `access` token from the response!**

---

### **3. Generate Audio Interview Questions**

**POST** `http://localhost:8000/api/audio-interview/questions/`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json
```

**Body:**
```json
{
  "job_description": "Senior Full Stack Developer position requiring 5+ years experience with React, Node.js, PostgreSQL. Must have experience with microservices architecture, CI/CD pipelines, and team leadership.",
  "question_count": 3,
  "difficulty": "medium",
  "voice_id": "browser-default",
  "language": "en"
}
```

**Expected Response:**
```json
{
  "session_id": "new-session-uuid",
  "questions": [
    {
      "id": "question-1-uuid",
      "question": "Tell me about a challenging project...",
      "category": "behavioral",
      "difficulty": "medium",
      "tips": "Use STAR method",
      "audio_duration": 4.5,
      "has_audio": false
    }
  ],
  "instructions": "Listen to each question, record your audio answer..."
}
```

✅ **Save the `session_id` and question `id`s!**

---

### **4. Get Question Data (for TTS)**

**GET** `http://localhost:8000/api/audio-interview/question/{question_id}/audio/`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
```

**Expected Response:**
```json
{
  "question_id": "uuid",
  "question": "Tell me about a challenging project...",
  "session": {
    "voice_id": "browser-default",
    "language": "en"
  },
  "audio_duration": 4.5,
  "instruction": "Use browser Web Speech API for TTS"
}
```

**Now use this question text with browser TTS!**

---

### **5. Test Browser TTS**

Open browser console and run:
```javascript
// Test browser TTS
const synth = window.speechSynthesis;
const utterance = new SpeechSynthesisUtterance("Tell me about a challenging project you led");
synth.speak(utterance);

// To stop
synth.cancel();
```

**You should hear the text being read aloud!**

---

### **6. Record Audio Answer**

In browser console:
```javascript
// Create audio recorder
const mediaRecorder = navigator.mediaDevices.getUserMedia({ audio: true })
  .then(stream => {
    const recorder = new MediaRecorder(stream);
    const chunks = [];
    
    recorder.ondataavailable = e => chunks.push(e.data);
    recorder.onstop = () => {
      const audioBlob = new Blob(chunks, { type: 'audio/webm' });
      console.log('Audio recorded:', audioBlob.size, 'bytes');
      // Use this blob for submission
    };
    
    recorder.start();
    setTimeout(() => recorder.stop(), 5000); // Record for 5 seconds
  });
```

---

### **7. Submit Audio Answer**

**POST** `http://localhost:8000/api/audio-interview/submit-answer/`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: multipart/form-data
```

**Form Data:**
```
question_id: question-1-uuid
audio_file: [your recorded audio blob]
transcribed_text: "My answer about the challenging project..."
transcription_confidence: 0.85
```

**Expected Response:**
```json
{
  "answer_id": "answer-uuid",
  "question_id": "question-1-uuid",
  "audio_file_path": "audio/answers/answer_uuid.webm",
  "transcribed_text": "My answer...",
  "audio_duration": 5.2,
  "transcription_confidence": 0.85,
  "submitted_at": "2024-01-15T..."
}
```

---

### **8. Get Batch Evaluation**

**POST** `http://localhost:8000/api/audio-interview/submit-all-answers/`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json
```

**Body:**
```json
{
  "session_id": "session-id-from-step-3"
}
```

**Expected Response:**
```json
{
  "session_id": "session-uuid",
  "total_questions": 3,
  "total_evaluations": 3,
  "average_score": 82.5,
  "evaluations": [
    {
      "evaluation_id": "eval-uuid",
      "question": "Tell me about...",
      "transcribed_text": "My answer...",
      "evaluation": {
        "overall_score": 85,
        "strengths": ["Clear examples", "Good structure"],
        "weaknesses": ["Could be more specific"],
        "improvement_tips": ["Add metrics", "Detail challenges"],
        "follow_up_questions": ["What was the impact?"]
      }
    }
  ],
  "session_complete": true,
  "interview_type": "audio"
}
```

---

### **9. Check History**

**GET** `http://localhost:8000/api/audio-interview/history/`

**Query Params (optional):**
- `limit=10` - number of sessions
- `session_id=xxx` - specific session details

**Expected Response:**
```json
{
  "sessions": [
    {
      "id": "session-uuid",
      "job_description": "Senior Full Stack Developer...",
      "question_count": 3,
      "answered_questions": 3,
      "completion_rate": 100,
      "average_score": 82.5,
      "interview_type": "audio"
    }
  ],
  "total_sessions": 2
}
```

---

## 🧪 Quick Browser Test

### **Test TTS in Browser Console:**
```javascript
// Get question
fetch('/api/audio-interview/question/uuid/audio/', {
  headers: { 'Authorization': 'Bearer TOKEN' }
})
.then(r => r.json())
.then(data => {
  // Speak question
  const synth = window.speechSynthesis;
  const utterance = new SpeechSynthesisUtterance(data.question);
  synth.speak(utterance);
});
```

### **Test STT in Browser Console:**
```javascript
const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.continuous = false;
recognition.onresult = e => console.log(e.results[0][0].transcript);
recognition.start();
```

---

## 📝 Using Postman

### **Collection to Test:**

1. **Generate Questions**
   - Method: POST
   - URL: `http://localhost:8000/api/audio-interview/questions/`
   - Headers: Authorization + Content-Type
   - Body: JSON with job_description

2. **Get Question Data**
   - Method: GET
   - URL: `http://localhost:8000/api/audio-interview/question/{id}/audio/`
   - Headers: Authorization

3. **Submit Answer**
   - Method: POST
   - URL: `http://localhost:8000/api/audio-interview/submit-answer/`
   - Body: form-data with question_id + audio_file

4. **Get Evaluation**
   - Method: POST
   - URL: `http://localhost:8000/api/audio-interview/submit-all-answers/`
   - Body: JSON with session_id

5. **Check History**
   - Method: GET
   - URL: `http://localhost:8000/api/audio-interview/history/`

---

## ✅ Expected Results

- ✅ Questions generated with Fireworks AI
- ✅ Question text returned for browser TTS
- ✅ Audio recorded and uploaded
- ✅ Transcription stored (manual or automatic)
- ✅ Batch evaluation with AI feedback
- ✅ History tracking working

---

## 🚀 That's it!

Your audio interview system now works **WITHOUT OpenAI** using:
- Browser TTS for questions
- Browser STT for transcription
- Fireworks AI for evaluation

No API keys needed beyond Fireworks! 🎉
