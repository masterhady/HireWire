# 🎤 Audio Interview Testing Guide

## Overview
The audio interview system now uses **browser-based TTS** for questions and **OpenAI Whisper** for speech-to-text transcription. This approach is more efficient and doesn't require server-side audio file storage.

## System Architecture
- **Question Audio**: Browser Text-to-Speech (Web Speech API)
- **Answer Transcription**: OpenAI Whisper API
- **AI Evaluation**: Fireworks AI
- **Authentication**: JWT tokens

## Quick Test

### 1. Open the Test Page
```bash
# Open the test HTML file in your browser
open test_audio.html
# or navigate to: file:///home/mariem/HireWire/test_audio.html
```

### 2. Test with Pre-configured Question
The test page is pre-configured with:
- **Question ID**: `1531cb58-6a25-4df3-80ab-ac8ef2c0e963`
- **JWT Token**: Already filled in (valid until expiration)

### 3. Test Steps
1. **Load Question**: Click "Load Question" button
2. **Play Audio**: Click "Play Question Audio" to hear the question using browser TTS
3. **Record Answer**: Click "Start Recording" and speak your answer
4. **Stop Recording**: Click "Stop & Get Transcription" to transcribe your answer
5. **Submit**: Click "Submit Answer" to send to the API

## API Endpoints

### 1. Generate Questions
```bash
POST http://localhost:8000/api/audio-interview/questions/
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
    "job_description": "Senior Full Stack Developer with React and Node.js experience",
    "difficulty": "medium",
    "voice_id": "alloy",
    "language": "en"
}
```

### 2. Get Question Text (for TTS)
```bash
GET http://localhost:8000/api/audio-interview/question/{question_id}/audio/
Authorization: Bearer <JWT_TOKEN>
```

**Response:**
```json
{
    "question_text": "Can you describe your experience with React and how you handle state management?",
    "voice_id": "alloy",
    "language": "en"
}
```

### 3. Submit Audio Answer
```bash
POST http://localhost:8000/api/audio-interview/submit-answer/
Authorization: Bearer <JWT_TOKEN>
Content-Type: multipart/form-data

{
    "question_id": "1531cb58-6a25-4df3-80ab-ac8ef2c0e963",
    "audio_file": <audio_file>,
    "transcribed_text": "I have 3 years of experience with React...",
    "transcription_confidence": "0.9"
}
```

### 4. Batch Submit All Answers
```bash
POST http://localhost:8000/api/audio-interview/submit-all-answers/
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
    "session_id": "c4839020-3a2e-4678-bda4-ee465013fe80",
    "answers": [
        {
            "question_id": "1531cb58-6a25-4df3-80ab-ac8ef2c0e963",
            "transcribed_text": "I have 3 years of experience with React...",
            "transcription_confidence": "0.9"
        }
    ]
}
```

## Browser Compatibility

### Text-to-Speech (TTS)
- ✅ Chrome/Chromium
- ✅ Firefox
- ✅ Safari
- ✅ Edge

### Speech Recognition (STT)
- ✅ Chrome/Chromium
- ✅ Edge
- ⚠️ Firefox (limited support)
- ⚠️ Safari (limited support)

## Troubleshooting

### 1. "Question not found or access denied"
- **Cause**: Question ID doesn't exist or user doesn't have access
- **Solution**: Generate new questions using the questions API

### 2. "No audio file available"
- **Cause**: This is expected - we use browser TTS, not server audio files
- **Solution**: Use the "Play Question Audio" button for browser TTS

### 3. "Speech recognition not supported"
- **Cause**: Browser doesn't support Web Speech API
- **Solution**: Use Chrome/Edge or manually type the transcribed text

### 4. "TTS Error" in console
- **Cause**: OpenAI TTS API key doesn't have TTS access
- **Solution**: This is expected - we use browser TTS instead

## Testing with cURL

### Generate Questions
```bash
curl -X POST http://localhost:8000/api/audio-interview/questions/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzYxNjgwMDUyLCJpYXQiOjE3NjE2NzY0NTIsImp0aSI6IjMwZDc0NDQ4N2Y4NjQzODZhZDY5MGZkMjI1YTg0ZTRhIiwidXNlcl9pZCI6MjEsInJvbGUiOiJqb2JzZWVrZXIiLCJ1c2VybmFtZSI6InNlZWtlcjEifQ.C5wPJdZ7gyqBpY_pEjrxllOb-PlY4KPBoBNGoL0CVhQ" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "Senior Full Stack Developer with React and Node.js experience",
    "difficulty": "medium",
    "voice_id": "alloy",
    "language": "en"
  }'
```

### Get Question Text
```bash
curl -X GET http://localhost:8000/api/audio-interview/question/1531cb58-6a25-4df3-80ab-ac8ef2c0e963/audio/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzYxNjgwMDUyLCJpYXQiOjE3NjE2NzY0NTIsImp0aSI6IjMwZDc0NDQ4N2Y4NjQzODZhZDY5MGZkMjI1YTg0ZTRhIiwidXNlcl9pZCI6MjEsInJvbGUiOiJqb2JzZWVrZXIiLCJ1c2VybmFtZSI6InNlZWtlcjEifQ.C5wPJdZ7gyqBpY_pEjrxllOb-PlY4KPBoBNGoL0CVhQ"
```

## Expected Flow

1. **Generate Questions** → Get question IDs
2. **Load Question** → Get question text for TTS
3. **Play Audio** → Browser speaks the question
4. **Record Answer** → User speaks their answer
5. **Transcribe** → Browser transcribes the audio
6. **Submit Answer** → Send to API for evaluation
7. **Get Results** → Receive AI evaluation

## Notes

- The system no longer generates server-side audio files
- All TTS is handled by the browser's Web Speech API
- STT uses OpenAI Whisper for accurate transcription
- The JWT token in the test file is valid until expiration
- Questions are stored in the database but audio is generated on-demand by the browser
