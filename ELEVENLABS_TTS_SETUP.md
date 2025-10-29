# 🎤 ElevenLabs TTS Setup Guide

## Overview
ElevenLabs provides high-quality text-to-speech that can replace OpenAI TTS. It offers a free tier with 10,000 characters per month.

## Setup Steps

### 1. Get ElevenLabs API Key
1. Go to [ElevenLabs](https://elevenlabs.io/)
2. Sign up for a free account
3. Go to your profile settings
4. Copy your API key

### 2. Add API Key to Environment
Add to your `.env` file:
```bash
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

### 3. Test the Setup
```bash
# Test ElevenLabs TTS
cd /home/mariem/HireWire
source venv/bin/activate
python -c "
from elevenlabs import generate
audio = generate('Hello, this is a test of ElevenLabs TTS.')
print('✅ ElevenLabs TTS working!')
"
```

## How It Works

### With ElevenLabs API Key:
1. **Question Generation** → ElevenLabs generates high-quality audio
2. **Audio Storage** → Server stores the audio file
3. **Audio Serving** → Server serves the audio file to client
4. **Client Plays** → Browser plays the AI-generated audio

### Without ElevenLabs API Key (Fallback):
1. **Question Generation** → No audio generated
2. **Client Requests** → Server returns question text
3. **Browser TTS** → Browser speaks the question

## API Behavior

### When ElevenLabs is Available:
```bash
GET /api/audio-interview/question/{id}/audio/
# Returns: Audio file (MP3)
```

### When ElevenLabs is Not Available:
```bash
GET /api/audio-interview/question/{id}/audio/
# Returns: JSON with question text
{
    "question_text": "Can you describe your experience with React?",
    "voice_id": "alloy",
    "language": "en"
}
```

## Voice Options

ElevenLabs provides multiple voices:
- **Alloy** (default) - Neutral, professional
- **Echo** - Warm, friendly
- **Fable** - British accent
- **Onyx** - Deep, authoritative
- **Nova** - Young, energetic
- **Shimmer** - Soft, gentle

## Cost Information

- **Free Tier**: 10,000 characters/month
- **Starter Plan**: $5/month for 30,000 characters
- **Creator Plan**: $22/month for 100,000 characters

## Testing

1. **Set up ElevenLabs API key**
2. **Generate new questions** (old questions won't have audio)
3. **Test audio playback** in the test page
4. **Check server logs** for TTS generation

## Troubleshooting

### "ElevenLabs TTS Error"
- Check API key is correct
- Check API key has sufficient credits
- Check internet connection

### "No audio file available"
- Question was generated before ElevenLabs setup
- Generate new questions to get audio

### Audio Quality Issues
- Try different voices
- Check text length (very long text may have issues)
- Ensure stable internet connection
