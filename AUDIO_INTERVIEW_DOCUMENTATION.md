# 🎤 Audio Interview System Documentation

## 🌟 Overview

The Audio Interview System provides a realistic, voice-based interview experience with AI-powered question generation, automatic speech transcription, and comprehensive evaluation. This feature transforms traditional text-based interviews into immersive audio conversations.

## 🏗️ Architecture

### **Core Components:**
- **Text-to-Speech (TTS)**: OpenAI TTS API converts questions to natural speech
- **Speech-to-Text (STT)**: OpenAI Whisper API transcribes user answers
- **AI Evaluation**: Fireworks AI provides comprehensive feedback on transcribed answers
- **Audio Storage**: Django file storage for question and answer audio files
- **Batch Processing**: Holistic evaluation of complete interview sessions

### **Audio Flow:**
```
1. Generate Questions → 2. TTS Conversion → 3. Audio Playback
                                              ↓
6. Batch Evaluation ← 5. STT Transcription ← 4. Audio Recording
```

---

## 🎯 API Endpoints

### 1. Generate Audio Interview Questions
**POST** `/audio-interview/questions/`

**Description:** Generate AI-powered interview questions with automatic TTS conversion.

**Request Body:**
```json
{
  "job_description": "string (required)",
  "cv_id": "uuid (optional)",
  "cv_text": "string (optional)",
  "question_count": 5,
  "difficulty": "medium",
  "voice_id": "alloy",
  "language": "en"
}
```

**Voice Options:**
- `alloy` - Balanced, natural voice
- `echo` - Clear, professional tone
- `fable` - Warm, engaging voice
- `onyx` - Deep, authoritative voice
- `nova` - Bright, energetic voice
- `shimmer` - Soft, pleasant voice

**Response:**
```json
{
  "session_id": "uuid",
  "questions": [
    {
      "id": "question-uuid",
      "question": "Tell me about a challenging project you led",
      "category": "behavioral",
      "difficulty": "medium",
      "tips": "Use STAR method",
      "expected_answer_focus": "leadership and problem-solving",
      "audio_file_path": "audio/questions/question_uuid.mp3",
      "audio_duration": 4.2,
      "has_audio": true
    }
  ],
  "voice_id": "alloy",
  "language": "en",
  "instructions": "Listen to each question, record your audio answer, then use /api/audio-interview/submit-all-answers/ for batch evaluation.",
  "flow": "audio_batch_processing"
}
```

---

### 2. Get Question Audio
**GET** `/audio-interview/question/{question_id}/audio/`

**Description:** Serve the TTS-generated audio file for a specific question.

**Response:** MP3 audio file stream

**Usage:**
```html
<audio controls>
  <source src="/api/audio-interview/question/{question_id}/audio/" type="audio/mpeg">
</audio>
```

---

### 3. Submit Audio Answer
**POST** `/audio-interview/submit-answer/`

**Description:** Submit recorded audio answer with automatic transcription.

**Request:** `multipart/form-data`
```
question_id: uuid (required)
audio_file: file (required) - .mp3, .wav, .webm, .m4a
```

**Response:**
```json
{
  "answer_id": "uuid",
  "question_id": "uuid",
  "audio_file_path": "audio/answers/answer_uuid.mp3",
  "transcribed_text": "I led a team of 5 developers to build...",
  "audio_duration": 45.3,
  "transcription_confidence": 0.92,
  "submitted_at": "2024-01-15T10:35:00Z"
}
```

---

### 4. Batch Submit All Audio Answers
**POST** `/audio-interview/submit-all-answers/`

**Description:** Evaluate all audio answers in a session using batch AI processing.

**Request Body:**
```json
{
  "session_id": "uuid (required)"
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "total_questions": 5,
  "total_evaluations": 5,
  "average_score": 84.2,
  "evaluations": [
    {
      "evaluation_id": "uuid",
      "answer_id": "uuid",
      "question_id": "uuid",
      "question": "Tell me about a challenging project...",
      "transcribed_text": "I led a team of 5 developers...",
      "audio_duration": 45.3,
      "transcription_confidence": 0.92,
      "evaluation": {
        "overall_score": 87,
        "strengths": ["Clear communication", "Specific examples", "Good structure"],
        "weaknesses": ["Could include more metrics", "Minor transcription unclear"],
        "correct_answer": "The ideal answer would include...",
        "answer_analysis": "Your response demonstrates strong leadership...",
        "improvement_tips": ["Add quantifiable results", "Speak more clearly"],
        "follow_up_questions": ["What was the project's ROI?", "How did you handle conflicts?"]
      }
    }
  ],
  "session_complete": true,
  "interview_type": "audio",
  "voice_id": "alloy",
  "language": "en",
  "message": "All audio answers evaluated successfully using batch AI processing"
}
```

---

### 5. Audio Interview History
**GET** `/audio-interview/history/`

**Description:** Get user's audio interview history and progress.

**Query Parameters:**
- `limit` (optional): Number of sessions (default: 10)
- `session_id` (optional): Get specific session details

**Response (Summary):**
```json
{
  "sessions": [
    {
      "id": "uuid",
      "job_description": "Senior Developer position...",
      "difficulty": "medium",
      "voice_id": "alloy",
      "language": "en",
      "created_at": "2024-01-15T10:00:00Z",
      "question_count": 5,
      "answered_questions": 5,
      "completion_rate": 100,
      "average_score": 84.2,
      "interview_type": "audio"
    }
  ],
  "total_sessions": 15,
  "interview_type": "audio"
}
```

---

## 🔧 Technical Requirements

### **Environment Variables:**
```bash
# Required for audio features
OPENAI_API_KEY=your_openai_api_key_here
FIREWORKS_API_KEY=your_fireworks_api_key_here

# Optional audio settings
AUDIO_STORAGE_PATH=/path/to/audio/files
MAX_AUDIO_FILE_SIZE=50MB
SUPPORTED_AUDIO_FORMATS=mp3,wav,webm,m4a
```

### **Dependencies:**
```bash
pip install openai>=1.40.0  # For Whisper STT and TTS
pip install requests>=2.31.0  # For API calls
```

### **Storage Requirements:**
- **Question Audio**: ~50KB per question (TTS MP3)
- **Answer Audio**: ~1-5MB per answer (user recording)
- **Estimated**: 10MB per complete interview session

---

## 🎮 Frontend Integration

### **Audio Recording (JavaScript):**
```javascript
class AudioRecorder {
  constructor() {
    this.mediaRecorder = null;
    this.audioChunks = [];
  }

  async startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.mediaRecorder = new MediaRecorder(stream);
    
    this.mediaRecorder.ondataavailable = (event) => {
      this.audioChunks.push(event.data);
    };
    
    this.mediaRecorder.start();
  }

  stopRecording() {
    return new Promise((resolve) => {
      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
        resolve(audioBlob);
      };
      this.mediaRecorder.stop();
    });
  }
}

// Usage
const recorder = new AudioRecorder();
await recorder.startRecording();
// ... user speaks ...
const audioBlob = await recorder.stopRecording();

// Submit audio answer
const formData = new FormData();
formData.append('question_id', questionId);
formData.append('audio_file', audioBlob, 'answer.wav');

const response = await fetch('/api/audio-interview/submit-answer/', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: formData
});
```

### **Audio Playback:**
```javascript
// Play question audio
const playQuestion = (questionId) => {
  const audio = new Audio(`/api/audio-interview/question/${questionId}/audio/`);
  audio.play();
};

// Complete interview flow
const conductAudioInterview = async (sessionId, questions) => {
  const answers = [];
  
  for (const question of questions) {
    // Play question
    await playQuestion(question.id);
    
    // Record answer
    const recorder = new AudioRecorder();
    await recorder.startRecording();
    // ... wait for user to finish ...
    const audioBlob = await recorder.stopRecording();
    
    // Submit answer
    const formData = new FormData();
    formData.append('question_id', question.id);
    formData.append('audio_file', audioBlob, 'answer.wav');
    
    const response = await fetch('/api/audio-interview/submit-answer/', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });
    
    answers.push(await response.json());
  }
  
  // Submit for batch evaluation
  const evaluation = await fetch('/api/audio-interview/submit-all-answers/', {
    method: 'POST',
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ session_id: sessionId })
  });
  
  return evaluation.json();
};
```

---

## 📊 Performance Considerations

### **TTS Generation:**
- **Speed**: ~2-5 seconds per question
- **Quality**: High-quality natural voices
- **Caching**: Audio files stored for reuse

### **STT Transcription:**
- **Accuracy**: 90-95% for clear speech
- **Speed**: ~5-15 seconds per minute of audio
- **Languages**: 50+ languages supported

### **Batch Evaluation:**
- **Processing**: 15-30 seconds for 5 questions
- **Context**: Full session analysis for better feedback
- **Scalability**: Handles sessions up to 20 questions

---

## 🔒 Security & Privacy

### **Audio File Security:**
- Files stored with UUID names (no personal info)
- User-specific access control (JWT authentication)
- Automatic cleanup of old audio files (optional)

### **Data Privacy:**
- Audio transcriptions stored securely
- No audio sent to third parties except OpenAI APIs
- User consent required for audio recording

### **API Rate Limits:**
- OpenAI TTS: 500 requests/day (free tier)
- OpenAI Whisper: 50 hours/month (free tier)
- Consider upgrading for production use

---

## 🧪 Testing Guide

### **Postman Testing:**

1. **Generate Audio Questions:**
```bash
POST /api/audio-interview/questions/
Authorization: Bearer <token>
Content-Type: application/json

{
  "job_description": "Senior Developer role...",
  "question_count": 3,
  "voice_id": "alloy"
}
```

2. **Play Question Audio:**
```bash
GET /api/audio-interview/question/{question_id}/audio/
Authorization: Bearer <token>
```

3. **Submit Audio Answer:**
```bash
POST /api/audio-interview/submit-answer/
Authorization: Bearer <token>
Content-Type: multipart/form-data

question_id: {question_id}
audio_file: [select audio file]
```

4. **Batch Evaluation:**
```bash
POST /api/audio-interview/submit-all-answers/
Authorization: Bearer <token>
Content-Type: application/json

{
  "session_id": "{session_id}"
}
```

### **Audio File Formats:**
- **Supported**: MP3, WAV, WebM, M4A
- **Recommended**: WAV (best quality) or MP3 (smaller size)
- **Max Size**: 50MB per file
- **Sample Rate**: 16kHz+ recommended

---

## 🚀 Deployment Notes

### **Production Setup:**
1. Configure OpenAI API keys
2. Set up audio file storage (local or cloud)
3. Configure CORS for audio streaming
4. Set up audio file cleanup cron job
5. Monitor API usage and costs

### **Scaling Considerations:**
- Use cloud storage (AWS S3, Google Cloud) for audio files
- Implement audio file compression
- Add CDN for faster audio delivery
- Consider audio streaming for large files

---

## 🎯 Future Enhancements

### **Planned Features:**
- **Real-time STT**: Live transcription during recording
- **Voice Analysis**: Pace, tone, confidence detection
- **Multi-language**: Support for non-English interviews
- **Custom Voices**: User-selectable interviewer voices
- **Audio Feedback**: TTS-generated evaluation feedback

### **Advanced Features:**
- **Emotion Detection**: Analyze speech patterns for confidence
- **Pronunciation Analysis**: Feedback on speech clarity
- **Interview Coaching**: Real-time tips during recording
- **Video Integration**: Combined audio-video interviews

---

This audio interview system provides a comprehensive, production-ready solution for voice-based interview practice with AI evaluation! 🎤✨
