# 🚀 OpenAI TTS Upgrade Guide

## Current Issue
Your OpenAI API key doesn't have access to TTS models (`tts-1`, `tts-1-hd`). This is a common limitation with free/credit-based accounts.

## Solutions

### Option 1: Upgrade to OpenAI Pro Plan (Recommended)
1. **Go to**: [OpenAI Platform](https://platform.openai.com/)
2. **Navigate to**: Billing → Plans
3. **Select**: Pro Plan ($20/month)
4. **Benefits**:
   - Access to all TTS models
   - Higher rate limits
   - Priority support
   - More API credits

### Option 2: Request TTS Access
1. **Contact**: OpenAI Support
2. **Request**: TTS access for your current plan
3. **Provide**: Use case and justification
4. **Wait**: Response within 1-2 business days

### Option 3: Use Different API Key
1. **Create**: New OpenAI account
2. **Upgrade**: To Pro plan
3. **Update**: Your `.env` file with new key
4. **Test**: TTS functionality

## After Getting TTS Access

### 1. Update Your Code
The system will automatically detect TTS access and use OpenAI instead of ElevenLabs.

### 2. Test TTS
```bash
# Test OpenAI TTS
cd /home/mariem/HireWire
source venv/bin/activate
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from decouple import config
import requests

openai_key = config('OPENAI_API_KEY')
tts_url = 'https://api.openai.com/v1/audio/speech'
headers = {'Authorization': f'Bearer {openai_key}', 'Content-Type': 'application/json'}
payload = {'model': 'tts-1', 'input': 'Hello, this is a test.', 'voice': 'alloy', 'response_format': 'mp3'}

response = requests.post(tts_url, headers=headers, json=payload)
print(f'Status: {response.status_code}')
if response.ok:
    print('✅ OpenAI TTS working!')
else:
    print(f'❌ Error: {response.text}')
"
```

### 3. Generate New Questions
Old questions won't have audio. Generate new ones to get OpenAI TTS audio.

## Cost Comparison

| Service | Cost | Quality | Setup |
|---------|------|---------|-------|
| **OpenAI TTS** | $20/month | High | Easy |
| **ElevenLabs** | Free tier available | Very High | Easy |
| **Browser TTS** | Free | Medium | None |

## Recommendation

**For production use**: Upgrade to OpenAI Pro plan
**For testing/development**: Use ElevenLabs free tier
**For quick testing**: Use browser TTS (current setup)

## Next Steps

1. **Choose your preferred solution**
2. **Set up the TTS service**
3. **Test the audio generation**
4. **Generate new questions with audio**
5. **Test the complete flow**
