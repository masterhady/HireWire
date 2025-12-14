"""
WebSocket consumer for OpenAI Realtime API integration.

Handles real-time conversational HR interviews using OpenAI's Realtime API.
"""

import json
import asyncio
import base64
import websockets
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from decouple import config
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RealtimeInterviewConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that bridges browser ↔ Django ↔ OpenAI Realtime API.
    
    Flow:
    1. Browser connects to Django WebSocket
    2. Django establishes connection to OpenAI Realtime API
    3. Audio/events flow bidirectionally through Django
    4. Conversation is stored in database
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.openai_ws = None
        self.session_id = None
        self.job_description = None
        self.openai_task = None
        
    async def connect(self):
        """Handle WebSocket connection from browser."""
        # Accept the WebSocket connection
        await self.accept()
        
        # Get OpenAI API key
        self.openai_api_key = config("OPENAI_API_KEY", default=None)
        if not self.openai_api_key:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "OPENAI_API_KEY not configured on server"
            }))
            await self.close()
            return
        
        logger.info(f"WebSocket connected for user: {self.scope['user']}")
        
        # Send connection success
        await self.send(text_data=json.dumps({
            "type": "connected",
            "message": "Connected to interview server. Initializing AI..."
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        logger.info(f"WebSocket disconnected with code: {close_code}")
        
        # Close OpenAI connection if exists
        if self.openai_ws:
            try:
                await self.openai_ws.close()
            except Exception as e:
                logger.error(f"Error closing OpenAI WebSocket: {e}")
        
        # Cancel OpenAI listener task
        if self.openai_task and not self.openai_task.done():
            self.openai_task.cancel()
    
    async def receive(self, text_data=None, bytes_data=None):
        """Handle messages from browser."""
        try:
            if text_data:
                data = json.loads(text_data)
                message_type = data.get("type")
                
                if message_type == "start_session":
                    # Initialize OpenAI Realtime API session
                    await self.start_realtime_session(data)
                    
                elif message_type == "audio":
                    # Forward audio to OpenAI
                    if self.openai_ws:
                        await self.send_audio_to_openai(data.get("audio"))
                    
                elif message_type == "stop_session":
                    # End the session
                    await self.end_session()
                    
            elif bytes_data:
                # Handle binary audio data
                if self.openai_ws:
                    await self.send_audio_bytes_to_openai(bytes_data)
                    
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Invalid JSON format"
            }))
        except Exception as e:
            logger.error(f"Error in receive: {e}")
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": str(e)
            }))
    
    async def start_realtime_session(self, data):
        """Initialize OpenAI Realtime API session."""
        try:
            self.job_description = data.get("job_description", "")
            self.session_id = data.get("session_id")
            
            # Connect to OpenAI Realtime API
            model = "gpt-4o-realtime-preview-2024-12-17"
            url = f"wss://api.openai.com/v1/realtime?model={model}"
            
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            self.openai_ws = await websockets.connect(url, extra_headers=headers)
            
            # Configure the session
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": self._get_system_instructions(),
                    "voice": "alloy",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500
                    },
                    "temperature": 0.8,
                }
            }
            
            await self.openai_ws.send(json.dumps(session_config))
            
            # Start listening to OpenAI responses
            self.openai_task = asyncio.create_task(self.listen_to_openai())
            
            # Send success message to browser
            await self.send(text_data=json.dumps({
                "type": "session_started",
                "message": "AI interviewer is ready. You can start speaking."
            }))
            
            logger.info(f"OpenAI Realtime session started for session_id: {self.session_id}")
            
        except Exception as e:
            logger.error(f"Error starting realtime session: {e}")
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": f"Failed to start AI session: {str(e)}"
            }))
    
    def _get_system_instructions(self) -> str:
        """Get system instructions for the AI interviewer."""
        base_instructions = (
            "You are a professional HR interviewer conducting a voice interview. "
            "Keep your questions conversational, clear, and concise. "
            "Ask follow-up questions based on the candidate's responses. "
            "Be friendly but professional. "
            "Focus on behavioral questions, cultural fit, and career goals. "
        )
        
        if self.job_description:
            base_instructions += f"\n\nTarget job description: {self.job_description}\n"
            base_instructions += "Tailor your questions to assess fit for this specific role."
        
        return base_instructions
    
    async def listen_to_openai(self):
        """Listen for messages from OpenAI Realtime API and forward to browser."""
        try:
            async for message in self.openai_ws:
                try:
                    event = json.loads(message)
                    event_type = event.get("type")
                    
                    # Forward relevant events to browser
                    if event_type == "response.audio.delta":
                        # Stream audio chunks to browser
                        audio_delta = event.get("delta")
                        if audio_delta:
                            await self.send(text_data=json.dumps({
                                "type": "audio_delta",
                                "audio": audio_delta
                            }))
                    
                    elif event_type == "response.audio_transcript.delta":
                        # Stream transcript
                        transcript_delta = event.get("delta")
                        if transcript_delta:
                            await self.send(text_data=json.dumps({
                                "type": "transcript_delta",
                                "text": transcript_delta,
                                "role": "assistant"
                            }))
                    
                    elif event_type == "conversation.item.input_audio_transcription.completed":
                        # User's speech transcription
                        transcript = event.get("transcript", "")
                        await self.send(text_data=json.dumps({
                            "type": "user_transcript",
                            "text": transcript
                        }))
                    
                    elif event_type == "response.done":
                        # Response completed
                        await self.send(text_data=json.dumps({
                            "type": "response_done"
                        }))
                    
                    elif event_type == "error":
                        # Error from OpenAI
                        error_message = event.get("error", {}).get("message", "Unknown error")
                        logger.error(f"OpenAI error: {error_message}")
                        await self.send(text_data=json.dumps({
                            "type": "error",
                            "message": f"AI error: {error_message}"
                        }))
                    
                    # Log other events for debugging
                    else:
                        logger.debug(f"OpenAI event: {event_type}")
                        
                except json.JSONDecodeError:
                    logger.error("Failed to decode OpenAI message")
                except Exception as e:
                    logger.error(f"Error processing OpenAI message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("OpenAI WebSocket connection closed")
            await self.send(text_data=json.dumps({
                "type": "ai_disconnected",
                "message": "AI connection closed"
            }))
        except Exception as e:
            logger.error(f"Error in OpenAI listener: {e}")
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": f"AI listener error: {str(e)}"
            }))
    
    async def send_audio_to_openai(self, audio_base64: str):
        """Send audio data to OpenAI Realtime API."""
        if not self.openai_ws:
            return
        
        try:
            audio_event = {
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }
            await self.openai_ws.send(json.dumps(audio_event))
        except Exception as e:
            logger.error(f"Error sending audio to OpenAI: {e}")
    
    async def send_audio_bytes_to_openai(self, audio_bytes: bytes):
        """Send binary audio data to OpenAI Realtime API."""
        if not self.openai_ws:
            return
        
        try:
            # Convert bytes to base64
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            await self.send_audio_to_openai(audio_base64)
        except Exception as e:
            logger.error(f"Error sending audio bytes to OpenAI: {e}")
    
    async def end_session(self):
        """End the interview session."""
        try:
            if self.openai_ws:
                await self.openai_ws.close()
                self.openai_ws = None
            
            await self.send(text_data=json.dumps({
                "type": "session_ended",
                "message": "Interview session ended"
            }))
            
            logger.info(f"Session ended for session_id: {self.session_id}")
            
        except Exception as e:
            logger.error(f"Error ending session: {e}")
