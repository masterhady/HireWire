# 🎤 Fireworks Audio Interview Setup (No OpenAI Required)

## ✅ **Solution: Browser-Based Audio + Fireworks AI**

Instead of using OpenAI for TTS/STT, we now use:
- **Browser Web Speech API** for TTS (client-side)
- **Browser Web Speech API** for STT (client-side)  
- **Fireworks AI** for question generation and evaluation

**Benefits:**
- ✅ No OpenAI API key needed
- ✅ Uses existing Fireworks AI key
- ✅ Free and unlimited (browser-based)
- ✅ No external API costs
- ✅ Privacy-friendly (stays in browser)

---

## 🏗️ **Architecture**

### **Text-to-Speech (TTS):**
- Client uses `window.speechSynthesis` API
- Native browser voices (OS-dependent)
- No server-side processing needed

### **Speech-to-Text (STT):**
- Client uses `SpeechRecognition` API  
- Real-time transcription
- Fallback to manual text input if unsupported

### **AI Evaluation:**
- Fireworks AI evaluates the transcribed answers
- Same comprehensive feedback as before

---

## 📋 **Setup Instructions**

### **1. Update Your .env File**
```bash
# You DON'T need OPENAI_API_KEY anymore!
# Remove it from your .env file:

# REMOVED: OPENAI_API_KEY=sk-...

# Keep only Fireworks settings:
FIREWORKS_API_KEY=fw_3ZPaFUzNMHy7FLpefcG5QJmS
EMBEDDING_PROVIDER=fireworks
```

### **2. Clear Old Audio Interview Data (Optional)**
If you want to start fresh:
```sql
-- In Supabase SQL editor or psql:
TRUNCATE TABLE audio_interview_questions;
TRUNCATE TABLE audio_interview_answers;
TRUNCATE TABLE audio_interview_evaluations;
```

### **3. Generate New Audio Interview Questions**
Now questions will work WITHOUT needing OpenAI!

```bash
POST http://localhost:8000/api/audio-interview/questions/
Authorization: Bearer <JWT_TOKEN>

{
  "job_description": "Senior Full Stack Developer...",
  "question_count": 3,
  "difficulty": "medium",
  "voice_id": "browser-default"  # Info only, uses browser voice
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "questions": [
    {
      "id": "uuid",
      "question": "Tell me about a challenging project...",
      "has_audio": false,  // Client will generate TTS
      "audio_duration": 4.2
    }
  ]
}
```

---

## 🎮 **Frontend Integration**

### **Include the Helper Script:**
```html
<script src="/static/js/audio_interview_helper.js"></script>
```

### **Generate TTS for Question:**
```javascript
const audioHelper = new AudioInterviewHelper();

// Get question data
const response = await fetch('/api/audio-interview/question/{id}/audio/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const questionData = await response.json();

// Generate TTS
audioHelper.speakQuestion(questionData.question)
  .then(() => console.log('Question audio played'))
  .catch(err => console.error('TTS error:', err));
```

### **Record Answer with Transcription:**
```javascript
const recognition = audioHelper.startRecording(
  (result) => {
    // Live transcription updates
    console.log('Transcript:', result.final || result.interim);
  },
  (error) => console.error('Recording error:', error)
);

// Stop after user finishes
setTimeout(() => {
  audioHelper.stopRecording();
  
  // Submit audio + transcription
  const formData = new FormData();
  formData.append('question_id', questionId);
  formData.append('audio_file', audioBlob);
  formData.append('transcribed_text', finalTranscript); // From recognition result
  formData.append('transcription_confidence', 0.95);
  
  fetch('/api/audio-interview/submit-answer/', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
  });
}, 60000);
```

---

## 📝 **Updated API Endpoints**

### **1. Get Question Data (TTS-ready):**
```
GET /api/audio-interview/question/{question_id}/audio/
```
Returns question text for client-side TTS.

### **2. Submit Audio Answer:**
```
POST /api/audio-interview/submit-answer/
Content-Type: multipart/form-data

question_id: uuid
audio_file: file
transcribed_text: string  # Optional - client STT result
transcription_confidence: float  # Optional
```

---

## 🧪 **Testing Without OpenAI**

### **Test TTS (Browser):**
```javascript
// In browser console:
const synth = window.speechSynthesis;
const utterance = new SpeechSynthesisUtterance("Test audio interview.");
synth.speak(utterance);
```

### **Test STT (Browser):**
```javascript
// In browser console:
const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.onresult = (e) => console.log(e.results[0][0].transcript);
recognition.start();
```

### **Test Complete Flow:**
1. Generate questions → Get session_id
2. Use helper to speak questions
3. Use helper to record and transcribe answers
4. Submit audio + transcription
5. Get Fireworks AI evaluation

---

## ✅ **Benefits of This Approach**

| Feature | OpenAI Approach | Fireworks + Browser Approach |
|---------|----------------|------------------------------|
| **TTS Quality** | High-quality voices | OS-dependent, varied |
| **STT Accuracy** | 95%+ accuracy | 80-90% accuracy |
| **Cost** | ~$0.015 per minute | FREE |
| **API Keys** | OpenAI required | Only Fireworks needed |
| **Privacy** | Audio sent to OpenAI | Stays in browser |
| **Latency** | Network delay | Instant |
| **Offline** | No | Partial (audio only) |

---

## 🎯 **Current Limitations**

1. **Browser Support:** 
   - Chrome/Edge: Full support ✅
   - Firefox: TTS only (no STT) ⚠️
   - Safari: Varies ⚠️

2. **Voice Quality:**
   - Depends on OS
   - No custom voices
   - Limited to OS voices

3. **Transcription:**
   - Less accurate than Whisper
   - Language-dependent
   - May require manual correction

---

## 💡 **Hybrid Approach (Optional)**

If you want to support both:

```javascript
// Use Fireworks-only first
if (hasFireworksKey && !hasOpenAIKey) {
  // Browser-based TTS/STT
} else if (hasOpenAIKey) {
  // Use OpenAI for better quality
} else {
  // Fallback: manual text input
}
```

---

## 🚀 **Next Steps**

1. Remove `OPENAI_API_KEY` from `.env`
2. Restart your Django server
3. Test audio interview with browser APIs
4. Frontend: Integrate the helper script
5. Generate new questions and test

No OpenAI key needed! 🎉
