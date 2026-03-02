"""
WebSocket consumer for Groq-based modular AI interview.

Uses Groq Whisper for STT and Groq Llama 3 for LLM.
The browser handles TTS using the Web Speech API.
"""

import json
import asyncio
import base64
import httpx
from channels.generic.websocket import AsyncWebsocketConsumer
from decouple import config
import logging
import io
import wave

logger = logging.getLogger(__name__)


class RealtimeInterviewConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that bridges browser ↔ Django ↔ Groq.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id = None
        self.job_description = None
        self.conversation_history = []
        self.is_processing = False
        
    async def connect(self):
        """Handle WebSocket connection from browser."""
        await self.accept()
        
        self.groq_api_key = config("GROQ_API_KEY", default=None)
        if not self.groq_api_key:
            logger.error("❌ GROQ_API_KEY not found in environment")
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "GROQ_API_KEY not configured on server"
            }))
            await self.close()
            return
        
        logger.info(f"✅ WebSocket connected from {self.scope.get('client', 'unknown')}")
        logger.info(f"🔑 GROQ_API_KEY found: {self.groq_api_key[:10]}...")
        
        await self.send(text_data=json.dumps({
            "type": "connected",
            "message": "Connected to Groq-powered interview server."
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        logger.info(f"WebSocket disconnected with code: {close_code}")
    
    async def receive(self, text_data=None, bytes_data=None):
        """Handle messages from browser."""
        try:
            if text_data:
                data = json.loads(text_data)
                message_type = data.get("type")
                logger.info(f"📨 Received message type: {message_type}")
                
                if message_type == "start_session":
                    logger.info("🎬 Starting session...")
                    await self.start_session(data)
                    
                elif message_type == "audio":
                    logger.info("🎤 Received audio data")
                    # In modular mode, we expect a full audio blob (base64)
                    await self.handle_audio_turn(data.get("audio"))
                    
                elif message_type == "stop_session":
                    logger.info("🛑 Stopping session...")
                    
                    # Generate feedback before ending session
                    if len(self.conversation_history) > 1:  # More than just system prompt
                        await self.generate_interview_feedback()
                    
                    await self.send(text_data=json.dumps({
                        "type": "session_ended",
                        "message": "Interview session ended"
                    }))
                    
        except Exception as e:
            logger.error(f"❌ Error in receive: {e}")
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": str(e)
            }))
    
    async def start_session(self, data):
        """Initialize the interview session."""
        self.job_description = data.get("job_description", "")
        self.session_id = data.get("session_id")
        logger.info(f"📋 Session ID: {self.session_id}")
        logger.info(f"💼 Job Description: {self.job_description[:50] if self.job_description else 'None'}...")
        
        # Initialize conversation history with system prompt
        self.conversation_history = [
            {"role": "system", "content": self._get_system_instructions()}
        ]
        logger.info(f"📝 Initialized conversation history with system prompt")
        
        # Trigger initial greeting
        logger.info("🤖 Generating initial AI greeting...")
        await self.generate_ai_response("The user has just joined. Please introduce yourself briefly and ask if they are ready.")
        
        await self.send(text_data=json.dumps({
            "type": "session_started",
            "message": "Groq AI interviewer is ready."
        }))
        logger.info("✅ Session started successfully")
    
    def _get_system_instructions(self) -> str:
        """Get system instructions for the AI interviewer."""
        instructions = (
            "You are a professional HR interviewer conducting a voice interview. "
            "Keep your responses conversational, clear, and concise (max 2-3 sentences). "
            "Ask follow-up questions based on the candidate's responses. "
            "Be friendly but professional. "
            "Focus on behavioral questions, cultural fit, and career goals. "
        )
        
        if self.job_description:
            instructions += f"\n\nTarget job description: {self.job_description}\n"
            instructions += "Tailor your questions to assess fit for this specific role."
        
        return instructions

    async def handle_audio_turn(self, audio_base64: str):
        """Process a full audio turn using Groq STT and LLM."""
        if self.is_processing:
            logger.warning("⚠️ Already processing, skipping this audio")
            return
        
        self.is_processing = True
        logger.info("🔄 Processing audio turn...")
        try:
            # 1. STT: Convert audio to text
            logger.info(f"🎧 Audio size: {len(audio_base64)} chars")
            transcript = await self.speech_to_text(audio_base64)
            if not transcript:
                logger.warning("⚠️ No transcript received from STT")
                self.is_processing = False
                return
            
            logger.info(f"📝 User said: {transcript}")
            
            # Send user transcript to browser for UI
            await self.send(text_data=json.dumps({
                "type": "user_transcript",
                "text": transcript
            }))
            
            # 2. LLM: Generate AI response
            logger.info("🤖 Generating AI response...")
            await self.generate_ai_response(transcript)
            
        except Exception as e:
            logger.error(f"❌ Error handling audio turn: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": f"Processing error: {str(e)}"
            }))
        finally:
            self.is_processing = False
            logger.info("✅ Audio turn processing complete")

    async def speech_to_text(self, audio_base64: str) -> str:
        """Call Groq Whisper API for STT."""
        try:
            logger.info("🎯 Decoding audio...")
            audio_data = base64.b64decode(audio_base64)
            logger.info(f"📊 Audio data size: {len(audio_data)} bytes")
            
            # Groq Whisper expects a file-like object
            files = {
                "file": ("audio.wav", audio_data, "audio/wav"),
                "model": (None, "whisper-large-v3"),
                "response_format": (None, "json"),
            }
            
            headers = {"Authorization": f"Bearer {self.groq_api_key}"}
            
            logger.info("🌐 Calling Groq Whisper API...")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers=headers,
                    files=files,
                    timeout=30.0
                )
                
                logger.info(f"📡 Groq STT Response Status: {response.status_code}")
                if response.status_code != 200:
                    logger.error(f"❌ Groq STT Error: {response.text}")
                    return ""
                
                result = response.json().get("text", "")
                logger.info(f"✅ STT Result: {result}")
                return result
                
        except Exception as e:
            logger.error(f"❌ STT Exception: {e}", exc_info=True)
            return ""

    async def generate_ai_response(self, user_text: str):
        """Call Groq LLM API for response."""
        try:
            logger.info(f"💬 Adding user message to history: {user_text[:50]}...")
            self.conversation_history.append({"role": "user", "content": user_text})
            
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": self.conversation_history,
                "temperature": 0.7,
                "max_tokens": 150
            }
            
            logger.info(f"🌐 Calling Groq LLM API (model: llama-3.3-70b-versatile)...")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                logger.info(f"📡 Groq LLM Response Status: {response.status_code}")
                if response.status_code != 200:
                    logger.error(f"❌ Groq LLM Error: {response.text}")
                    return
                
                ai_text = response.json()["choices"][0]["message"]["content"]
                logger.info(f"🤖 AI Response: {ai_text}")
                self.conversation_history.append({"role": "assistant", "content": ai_text})
                
                # Send text to browser for TTS and UI
                logger.info("📤 Sending AI response to browser...")
                await self.send(text_data=json.dumps({
                    "type": "transcript_delta", # Keep same type for frontend compatibility
                    "text": ai_text,
                    "role": "assistant"
                }))
                
                await self.send(text_data=json.dumps({
                    "type": "response_done"
                }))
                logger.info("✅ AI response sent successfully")
                
        except Exception as e:
            logger.error(f"❌ LLM Exception: {e}", exc_info=True)

    async def generate_interview_feedback(self):
        """Generate comprehensive feedback based on the interview conversation."""
        try:
            logger.info("📊 Generating interview feedback...")
            
            # Create a special prompt for feedback generation
            feedback_prompt = (
                "Based on the interview conversation above, provide comprehensive feedback for the candidate. "
                "Structure your response as follows:\n\n"
                "OVERALL ASSESSMENT:\n[2-3 sentences summarizing overall performance]\n\n"
                "STRENGTHS:\n- [Strength 1]\n- [Strength 2]\n- [Strength 3]\n\n"
                "AREAS FOR IMPROVEMENT:\n- [Improvement 1]\n- [Improvement 2]\n- [Improvement 3]\n\n"
                "RECOMMENDATIONS:\n- [Recommendation 1]\n- [Recommendation 2]\n- [Recommendation 3]\n\n"
                "Be specific, constructive, and professional. Focus on communication skills, "
                "clarity of responses, and overall interview performance."
            )
            
            # Create a temporary conversation for feedback
            feedback_messages = self.conversation_history + [
                {"role": "user", "content": feedback_prompt}
            ]
            
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": feedback_messages,
                "temperature": 0.5,  # Lower temperature for more consistent feedback
                "max_tokens": 800  # More tokens for detailed feedback
            }
            
            logger.info("🌐 Calling Groq LLM API for feedback generation...")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                logger.info(f"📡 Groq Feedback Response Status: {response.status_code}")
                if response.status_code != 200:
                    logger.error(f"❌ Groq Feedback Error: {response.text}")
                    return
                
                feedback_text = response.json()["choices"][0]["message"]["content"]
                logger.info(f"✅ Feedback generated successfully")
                logger.info(f"📝 Feedback preview: {feedback_text[:100]}...")
                
                # Parse the feedback into structured format
                feedback_data = self._parse_feedback(feedback_text)
                
                # Send feedback to browser
                logger.info("📤 Sending feedback to browser...")
                await self.send(text_data=json.dumps({
                    "type": "interview_feedback",
                    "feedback": feedback_data
                }))
                logger.info("✅ Feedback sent successfully")
                
        except Exception as e:
            logger.error(f"❌ Feedback Generation Exception: {e}", exc_info=True)
            # Send error feedback
            await self.send(text_data=json.dumps({
                "type": "interview_feedback",
                "feedback": {
                    "overall": "Thank you for completing the interview. We encountered an issue generating detailed feedback.",
                    "strengths": ["Participated in the interview"],
                    "improvements": ["Please try again later for detailed feedback"],
                    "recommendations": ["Continue practicing interview skills"]
                }
            }))
    
    def _parse_feedback(self, feedback_text: str) -> dict:
        """Parse the feedback text into structured format."""
        try:
            sections = {
                "overall": "",
                "strengths": [],
                "improvements": [],
                "recommendations": []
            }
            
            # Split by sections
            lines = feedback_text.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Detect section headers
                if "OVERALL ASSESSMENT" in line.upper():
                    current_section = "overall"
                    continue
                elif "STRENGTH" in line.upper():
                    current_section = "strengths"
                    continue
                elif "IMPROVEMENT" in line.upper() or "AREAS FOR IMPROVEMENT" in line.upper():
                    current_section = "improvements"
                    continue
                elif "RECOMMENDATION" in line.upper():
                    current_section = "recommendations"
                    continue
                
                # Add content to current section
                if current_section == "overall":
                    sections["overall"] += line + " "
                elif current_section in ["strengths", "improvements", "recommendations"]:
                    # Remove bullet points and add to list
                    clean_line = line.lstrip('- •*').strip()
                    if clean_line:
                        sections[current_section].append(clean_line)
            
            # Clean up overall assessment
            sections["overall"] = sections["overall"].strip()
            
            # Ensure we have at least some content
            if not sections["overall"]:
                sections["overall"] = "Thank you for participating in this interview. Your responses were noted."
            if not sections["strengths"]:
                sections["strengths"] = ["Completed the interview", "Engaged with the AI interviewer"]
            if not sections["improvements"]:
                sections["improvements"] = ["Continue practicing interview skills"]
            if not sections["recommendations"]:
                sections["recommendations"] = ["Keep practicing and refining your responses"]
            
            return sections
            
        except Exception as e:
            logger.error(f"Error parsing feedback: {e}")
            return {
                "overall": "Thank you for completing the interview.",
                "strengths": ["Participated in the interview"],
                "improvements": ["Continue developing your skills"],
                "recommendations": ["Practice more interviews"]
            }
