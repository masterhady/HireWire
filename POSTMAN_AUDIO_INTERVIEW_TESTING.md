# 🎤 Postman Audio Interview Testing Guide

## 📋 Prerequisites

1. **Server Running**: Django server on `http://localhost:8000`
2. **Authentication**: Valid JWT token from login
3. **OpenAI API Key**: Set in environment variables for TTS/STT
4. **CV Uploaded**: Have a CV uploaded for the user
5. **Audio Files**: Sample audio files for testing (.wav, .mp3, .webm)

---

## 🔐 Step 1: Authentication & Setup

### Login to Get JWT Token
```
POST http://localhost:8000/api/auth/login/
Content-Type: application/json

{
  "email": "your-email@example.com",
  "password": "your-password"
}
```

**Copy the `access` token for use in all subsequent requests.**

### Verify Environment Variables
Ensure these are set in your Django environment:
```bash
OPENAI_API_KEY=your_openai_api_key_here
FIREWORKS_API_KEY=your_fireworks_api_key_here
```

---

## 🎯 Step 2: Generate Audio Interview Questions

```
POST http://localhost:8000/api/audio-interview/questions/
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "job_description": "Senior Full Stack Developer position requiring 5+ years experience with React, Node.js, PostgreSQL, and AWS. Must have experience with microservices architecture, CI/CD pipelines, and team leadership. Strong problem-solving skills and ability to mentor junior developers required.",
  "question_count": 3,
  "difficulty": "medium",
  "voice_id": "alloy",
  "language": "en"
}
```

**Expected Response:**
```json
{
  "session_id": "audio-session-uuid-here",
  "questions": [
    {
      "id": "question-1-uuid",
      "question": "Tell me about a challenging full-stack project you led and how you managed the team",
      "category": "behavioral",
      "difficulty": "medium",
      "tips": "Use STAR method - Situation, Task, Action, Result",
      "expected_answer_focus": "leadership, technical skills, and project management",
      "audio_file_path": "audio/questions/question_uuid.mp3",
      "audio_duration": 6.8,
      "has_audio": true
    },
    {
      "id": "question-2-uuid",
      "question": "How do you approach debugging complex issues in a microservices architecture?",
      "category": "technical",
      "difficulty": "medium",
      "tips": "Discuss tools, methodologies, and systematic approaches",
      "expected_answer_focus": "problem-solving and technical expertise",
      "audio_file_path": "audio/questions/question_uuid.mp3",
      "audio_duration": 5.2,
      "has_audio": true
    }
  ],
  "voice_id": "alloy",
  "language": "en",
  "instructions": "Listen to each question, record your audio answer, then use /api/audio-interview/submit-all-answers/ for batch evaluation.",
  "flow": "audio_batch_processing"
}
```

**📝 Save the `session_id` and question `id`s for the next steps!**

---

## 🔊 Step 3: Play Question Audio

For each question, you can play the TTS-generated audio:

```
GET http://localhost:8000/api/audio-interview/question/QUESTION_1_ID/audio/
Authorization: Bearer YOUR_JWT_TOKEN
```

**Response:** MP3 audio file that you can play directly

**Testing Tips:**
- Use Postman's "Send and Download" to save the audio file
- Play the audio to verify TTS quality and clarity
- Test different voice_id options (alloy, echo, fable, onyx, nova, shimmer)

---

## 🎙️ Step 4: Record and Submit Audio Answers

### Prepare Audio Files
Create or record sample audio answers (30-60 seconds each):
- **Format**: .wav, .mp3, .webm, or .m4a
- **Content**: Professional interview responses
- **Quality**: Clear speech, minimal background noise

### Submit Audio Answer for Question 1
```
POST http://localhost:8000/api/audio-interview/submit-answer/
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: multipart/form-data

# Form data:
question_id: QUESTION_1_ID
audio_file: [select your recorded audio file]
```

**Expected Response:**
```json
{
  "answer_id": "answer-1-uuid",
  "question_id": "question-1-uuid",
  "audio_file_path": "audio/answers/answer_uuid.wav",
  "transcribed_text": "I led a team of 6 developers to build a microservices-based e-commerce platform. The main challenge was migrating from a monolithic architecture while maintaining zero downtime. I implemented a strangler fig pattern, gradually replacing components over 8 months. We used Docker containers, Kubernetes for orchestration, and implemented CI/CD with Jenkins. The project resulted in 40% better performance and 60% faster deployment cycles.",
  "audio_duration": 52.3,
  "transcription_confidence": 0.94,
  "submitted_at": "2024-01-15T10:35:00Z"
}
```

### Submit Audio Answer for Question 2
```
POST http://localhost:8000/api/audio-interview/submit-answer/
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: multipart/form-data

# Form data:
question_id: QUESTION_2_ID
audio_file: [select your second recorded audio file]
```

### Submit Audio Answer for Question 3
Repeat the same process for all remaining questions.

---

## 🧠 Step 5: Batch Audio Evaluation

After submitting all audio answers, get comprehensive AI evaluation:

```
POST http://localhost:8000/api/audio-interview/submit-all-answers/
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "session_id": "AUDIO_SESSION_ID_FROM_STEP_2"
}
```

**Expected Response:**
```json
{
  "session_id": "audio-session-uuid",
  "total_questions": 3,
  "total_evaluations": 3,
  "average_score": 86.7,
  "evaluations": [
    {
      "evaluation_id": "eval-1-uuid",
      "answer_id": "answer-1-uuid",
      "question_id": "question-1-uuid",
      "question": "Tell me about a challenging full-stack project you led...",
      "transcribed_text": "I led a team of 6 developers to build...",
      "audio_duration": 52.3,
      "transcription_confidence": 0.94,
      "evaluation": {
        "overall_score": 88,
        "strengths": [
          "Clear communication and confident delivery",
          "Specific technical details and metrics",
          "Good use of STAR method structure",
          "Demonstrates leadership and project management skills"
        ],
        "weaknesses": [
          "Could elaborate more on team challenges faced",
          "Missing details about stakeholder communication"
        ],
        "correct_answer": "The ideal answer would include specific project context, team dynamics, technical challenges, your leadership approach, measurable outcomes, and lessons learned...",
        "answer_analysis": "Your response demonstrates strong technical leadership with clear metrics and outcomes. The audio delivery was confident and well-structured. Consider adding more details about team management challenges and stakeholder interactions.",
        "improvement_tips": [
          "Add specific examples of team challenges and resolutions",
          "Include stakeholder management aspects",
          "Mention lessons learned and how they apply to future projects",
          "Consider speaking slightly slower for even better transcription accuracy"
        ],
        "follow_up_questions": [
          "How did you handle conflicts within the team during this migration?",
          "What was the total business impact and ROI of this project?",
          "What would you do differently if you had to lead a similar project again?"
        ]
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

## 📊 Step 6: View Audio Interview History

### Get Audio Interview Summary
```
GET http://localhost:8000/api/audio-interview/history/
Authorization: Bearer YOUR_JWT_TOKEN
```

### Get Detailed Audio Session
```
GET http://localhost:8000/api/audio-interview/history/?session_id=AUDIO_SESSION_ID
Authorization: Bearer YOUR_JWT_TOKEN
```

**Expected Response:**
```json
{
  "session": {
    "id": "audio-session-uuid",
    "user_id": "user-uuid",
    "job_description": "Senior Full Stack Developer position...",
    "difficulty": "medium",
    "voice_id": "alloy",
    "language": "en",
    "created_at": "2024-01-15T10:00:00Z"
  },
  "questions": [
    {
      "id": "question-uuid",
      "question": "Tell me about a challenging project...",
      "audio_file_path": "audio/questions/question_uuid.mp3",
      "audio_duration": 6.8,
      "answers": [
        {
          "id": "answer-uuid",
          "transcribed_text": "I led a team of 6 developers...",
          "audio_duration": 52.3,
          "transcription_confidence": 0.94,
          "evaluation": {
            "overall_score": 88,
            "strengths": ["Clear communication", "Specific details"],
            "improvement_tips": ["Add team challenge examples"]
          }
        }
      ]
    }
  ]
}
```

---

## 🧪 Advanced Testing Scenarios

### ✅ **Scenario 1: Different Voice Options**
Test all 6 TTS voices:
```json
{"voice_id": "alloy"}    // Balanced, natural
{"voice_id": "echo"}     // Clear, professional
{"voice_id": "fable"}    // Warm, engaging
{"voice_id": "onyx"}     // Deep, authoritative
{"voice_id": "nova"}     // Bright, energetic
{"voice_id": "shimmer"}  // Soft, pleasant
```

### ✅ **Scenario 2: Audio Quality Testing**
Test different audio formats and qualities:
- **High Quality**: 44.1kHz WAV files
- **Standard**: 16kHz MP3 files
- **Mobile**: WebM recordings from browser
- **Compressed**: Low-bitrate MP3 files

### ✅ **Scenario 3: Transcription Accuracy**
Test STT with various speech patterns:
- **Clear Speech**: Professional, slow pace
- **Fast Speech**: Rapid delivery
- **Accented Speech**: Non-native speakers
- **Technical Terms**: Industry jargon and acronyms
- **Background Noise**: Slight ambient sound

### ✅ **Scenario 4: Error Handling**
Test edge cases:
- **Large Audio Files**: >50MB uploads
- **Invalid Formats**: .txt, .pdf files
- **Corrupted Audio**: Damaged audio files
- **Missing OpenAI Key**: Test without API credentials
- **Network Issues**: Timeout scenarios

### ✅ **Scenario 5: Multi-language Support**
Test different languages:
```json
{"language": "en"}    // English
{"language": "es"}    // Spanish
{"language": "fr"}    // French
{"language": "de"}    // German
```

---

## 🔍 Performance Benchmarks

### **Expected Timing:**
- **Question Generation**: 5-15 seconds (includes TTS)
- **Audio Upload**: 1-5 seconds (depends on file size)
- **STT Transcription**: 5-20 seconds (depends on audio length)
- **Batch Evaluation**: 20-40 seconds (for 3-5 questions)

### **Audio File Sizes:**
- **Question Audio**: 50KB - 200KB per question
- **Answer Audio**: 500KB - 5MB per answer
- **Session Total**: 5MB - 25MB per complete interview

### **Transcription Accuracy:**
- **Clear Speech**: 95%+ accuracy
- **Normal Speech**: 90-95% accuracy
- **Challenging Audio**: 80-90% accuracy

---

## 🚨 Troubleshooting

### **Issue: "No audio file available"**
- **Cause**: TTS generation failed or OpenAI API key missing
- **Solution**: Check OpenAI API key and credits

### **Issue: "Transcription failed"**
- **Cause**: Audio file corrupted or unsupported format
- **Solution**: Use supported formats (.wav, .mp3, .webm, .m4a)

### **Issue: Low transcription confidence**
- **Cause**: Poor audio quality or background noise
- **Solution**: Record in quiet environment, speak clearly

### **Issue: "Audio file too large"**
- **Cause**: File exceeds size limit
- **Solution**: Compress audio or use shorter responses

### **Issue: TTS voice not working**
- **Cause**: Invalid voice_id parameter
- **Solution**: Use valid voices: alloy, echo, fable, onyx, nova, shimmer

---

## 📱 Frontend Integration Tips

### **Audio Recording (JavaScript):**
```javascript
// Start recording
const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
const mediaRecorder = new MediaRecorder(stream);
const audioChunks = [];

mediaRecorder.ondataavailable = (event) => {
  audioChunks.push(event.data);
};

mediaRecorder.start();

// Stop and submit
mediaRecorder.stop();
const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });

const formData = new FormData();
formData.append('question_id', questionId);
formData.append('audio_file', audioBlob, 'answer.wav');

fetch('/api/audio-interview/submit-answer/', {
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
```

---

## 🎯 Success Criteria

✅ **Questions Generated**: Session created with TTS audio files  
✅ **Audio Playback**: Questions play clearly with selected voice  
✅ **Audio Upload**: Files uploaded and stored successfully  
✅ **STT Transcription**: Speech converted to text with good accuracy  
✅ **AI Evaluation**: Comprehensive feedback considering audio quality  
✅ **History Tracking**: Complete audio sessions stored and retrievable  
✅ **Error Handling**: Graceful handling of audio processing failures  

---

This comprehensive audio interview system provides a realistic, voice-based interview experience with professional TTS voices, accurate speech recognition, and AI-powered evaluation! 🎤✨
