"""
WebSocket consumer for OpenAI Realtime API-based interview.

This consumer bridges browser ↔ Django ↔ OpenAI Realtime API WebSocket.
Uses OpenAI's Realtime API for real-time speech-to-speech conversations.
"""

import json
import asyncio
import base64
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from decouple import config

# Optional imports - handle gracefully if not available
try:
    import websockets
except ImportError:
    websockets = None
    logging.warning("websockets library not installed. Install with: pip install websockets")

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
    logging.warning("openai library not installed. Install with: pip install openai")

logger = logging.getLogger(__name__)


class OpenAIRealtimeInterviewConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that bridges browser ↔ Django ↔ OpenAI Realtime API.
    
    This connects to OpenAI's Realtime API WebSocket endpoint for real-time
    speech-to-speech conversations.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id = None
        self.job_description = None
        self.cv_text = None
        self.interview_type = "hr"
        self.openai_ws = None
        self.openai_task = None
        self.openai_api_key = config("OPENAI_API_KEY", default=None)
        self.initial_response_triggered = False
        
    async def connect(self):
        """Handle WebSocket connection from browser."""
        try:
            await self.accept()
            logger.info(f"✅ WebSocket connection accepted from {self.scope.get('client', 'unknown')}")
            
            # Check dependencies first
            if websockets is None:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "websockets library not installed. Server admin needs to run: pip install websockets"
                }))
                await self.close()
                return
            
            if OpenAI is None:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "openai library not installed. Server admin needs to run: pip install openai"
                }))
                await self.close()
                return
            
            if not self.openai_api_key:
                logger.error("❌ OPENAI_API_KEY not found in environment")
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "OPENAI_API_KEY not configured on server"
                }))
                await self.close()
                return
            
            logger.info(f"✅ WebSocket connected from {self.scope.get('client', 'unknown')}")
            await self.send(text_data=json.dumps({
                "type": "connected",
                "message": "Connected to OpenAI Realtime Interview server."
            }))
        except Exception as e:
            logger.error(f"❌ Error in WebSocket connect: {e}", exc_info=True)
            try:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": f"Connection error: {str(e)}"
                }))
            except:
                pass
            try:
                await self.close()
            except:
                pass
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        logger.info(f"WebSocket disconnected with code: {close_code}")
        
        # Close OpenAI WebSocket connection
        if self.openai_ws:
            await self.openai_ws.close()
        
        # Cancel OpenAI task
        if self.openai_task:
            self.openai_task.cancel()
            try:
                await self.openai_task
            except asyncio.CancelledError:
                pass
    
    async def receive(self, text_data=None, bytes_data=None):
        """Handle messages from browser."""
        try:
            if text_data:
                data = json.loads(text_data)
                message_type = data.get("type")
                logger.info(f"📨 Received message type: {message_type}")
                
                if message_type == "start_session":
                    await self.start_session(data)
                elif message_type == "audio_input":
                    await self.forward_audio_to_openai(data.get("audio"))
                elif message_type == "trigger_response":
                    await self.trigger_response()
                elif message_type == "stop_session":
                    await self.stop_session()
                    
        except Exception as e:
            logger.error(f"❌ Error in receive: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": str(e)
            }))
    
    async def start_session(self, data):
        """Initialize the interview session and connect to OpenAI Realtime API."""
        try:
            self.job_description = data.get("job_description", "")
            self.session_id = data.get("session_id")
            self.interview_type = data.get("interview_type", "hr")
            self.cv_text = data.get("cv_text", "")
            
            logger.info(f"🎬 Starting OpenAI Realtime session: {self.session_id}")
            logger.info(f"📋 Interview type: {self.interview_type}")
            logger.info(f"💼 Job description: {self.job_description[:50] if self.job_description else 'None'}...")
            
            # Check if OpenAI API key is available
            if not self.openai_api_key:
                error_msg = "OPENAI_API_KEY not configured on server"
                logger.error(f"❌ {error_msg}")
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": error_msg
                }))
                return
            
            # Build system prompt based on interview type and context
            system_prompt = self._build_system_prompt()
            logger.info(f"📝 System prompt length: {len(system_prompt)} characters")
            
            # Connect to OpenAI Realtime API WebSocket
            logger.info("🔌 Connecting to OpenAI Realtime API...")
            await self._connect_to_openai_realtime(system_prompt)
            logger.info("✅ Connected to OpenAI Realtime API - waiting for session.created event")
            
            # Note: session_started message will be sent when we receive session.created from OpenAI
            # This ensures the session is fully ready before notifying the frontend
            
        except Exception as e:
            error_msg = f"Failed to start session: {str(e)}"
            logger.error(f"❌ Error starting session: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": error_msg
            }))
    
    def _build_system_prompt(self):
        """Build system prompt for the interview."""
        if self.interview_type == "technical":
            base_prompt = (
                "You are a technical interviewer conducting a natural, conversational technical interview. "
                "Ask technical questions based on the candidate's CV and responses. "
                "Keep questions clear and appropriate for the candidate's experience level. "
                "Engage in a natural conversation, asking follow-up questions based on their answers."
            )
        else:  # hr
            base_prompt = (
                "You are an HR interviewer holding a natural, conversational interview. "
                "Ask behavioral and cultural fit questions. Keep questions short and conversational. "
                "Respond based on the candidate's message and ask relevant follow-up questions."
            )
        
        # Add CV context if available
        if self.cv_text:
            base_prompt += f"\n\nCandidate CV context:\n{self.cv_text[:1000]}"
        
        # Add job description if available
        if self.job_description:
            base_prompt += f"\n\nTarget job description: {self.job_description[:500]}"
        
        return base_prompt
    
    async def _connect_to_openai_realtime(self, system_prompt):
        """Connect to OpenAI Realtime API WebSocket."""
        try:
            # Check if websockets library is available
            if websockets is None:
                raise ImportError("websockets library is not installed. Install with: pip install websockets")
            
            # OpenAI Realtime API WebSocket URL
            ws_url = "wss://api.openai.com/v1/realtime?model=gpt-realtime-mini"
            
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            # Connect to OpenAI Realtime WebSocket
            self.openai_ws = await websockets.connect(ws_url, extra_headers=headers)
            
            # Send session configuration
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["audio", "text"],  # Prioritize audio
                    "instructions": system_prompt,
                    "voice": "alloy",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.3,  # More sensitive to catch interruptions
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 600  # Fast response
                    },
                    "temperature": 0.7,
                    "max_response_output_tokens": 4096,
                }
            }
            await self.openai_ws.send(json.dumps(session_config))
            
            logger.info("📋 Session configured with lenient turn detection settings")
            
            # Start task to receive messages from OpenAI
            self.openai_task = asyncio.create_task(self._receive_from_openai())
            
            logger.info("✅ Connected to OpenAI Realtime API")
            
        except Exception as e:
            logger.error(f"❌ Error connecting to OpenAI Realtime API: {e}", exc_info=True)
            raise
    
    async def _receive_from_openai(self):
        """Receive messages from OpenAI Realtime API and forward to browser."""
        try:
            async for message in self.openai_ws:
                try:
                    data = json.loads(message)
                    event_type = data.get("type")
                    
                    logger.info(f"📥 Received from OpenAI: {event_type}")
                    # Log full event data for debugging
                    if event_type not in ["session.created", "session.updated"]:
                        logger.info(f"📥 Full event data: {json.dumps(data, indent=2)}")
                    
                    # Handle different event types from OpenAI Realtime API
                    if event_type == "response.audio.delta":
                        # Audio chunk from OpenAI (base64 encoded PCM16)
                        audio_base64 = data.get("delta", "")
                        await self.send(text_data=json.dumps({
                            "type": "audio_output",
                            "audio": audio_base64
                        }))
                    
                    elif event_type == "response.audio_transcript.delta":
                        # Transcript delta from OpenAI
                        transcript_delta = data.get("delta", "")
                        await self.send(text_data=json.dumps({
                            "type": "transcript_delta",
                            "text": transcript_delta,
                            "role": "assistant"
                        }))
                    
                    elif event_type == "response.text.delta":
                        # Text delta from OpenAI
                        text_delta = data.get("delta", "")
                        await self.send(text_data=json.dumps({
                            "type": "text_delta",
                            "text": text_delta,
                            "role": "assistant"
                        }))
                    
                    elif event_type == "response.audio_transcript.done":
                        # Audio transcript complete
                        transcript = data.get("transcript", "")
                        await self.send(text_data=json.dumps({
                            "type": "transcript_complete",
                            "text": transcript,
                            "role": "assistant"
                        }))
                    
                    elif event_type == "response.done":
                        # Response complete
                        await self.send(text_data=json.dumps({
                            "type": "response_done"
                        }))
                    
                    elif event_type == "input_audio_buffer.speech_started":
                        # User started speaking - tell OpenAI to cancel current response
                        logger.info("🎤 Speech started - cancelling OpenAI response")
                        try:
                            await self.openai_ws.send(json.dumps({"type": "response.cancel"}))
                        except Exception as e:
                            logger.error(f"❌ Error cancelling response: {e}")
                            
                        await self.send(text_data=json.dumps({
                            "type": "speech_started"
                        }))
                    
                    elif event_type == "input_audio_buffer.speech_stopped":
                        # User stopped speaking
                        await self.send(text_data=json.dumps({
                            "type": "speech_stopped"
                        }))
                    
                    elif event_type == "conversation.item.input_audio_transcription.completed":
                        # User speech transcribed
                        transcript = data.get("transcript", "")
                        await self.send(text_data=json.dumps({
                            "type": "transcript_delta",
                            "text": transcript,
                            "role": "user"
                        }))
                    
                    elif event_type == "error":
                        # Error from OpenAI
                        error_obj = data.get("error", {})
                        error_message = error_obj.get("message", "Unknown error")
                        error_code = error_obj.get("code", "")
                        logger.error(f"❌ OpenAI Realtime API error: {error_code} - {error_message}")
                        await self.send(text_data=json.dumps({
                            "type": "error",
                            "message": error_message,
                            "code": error_code
                        }))
                    
                    elif event_type in ["session.created", "session.updated"]:
                        # Session events - log and send session_started if this is the first session.created
                        logger.info(f"📋 Session event: {event_type}")
                        
                        if event_type == "session.created":
                            # Send session_started message to client when OpenAI confirms session creation
                            try:
                                await self.send(text_data=json.dumps({
                                    "type": "session_started",
                                    "message": "Session started with OpenAI Realtime API"
                                }))
                                logger.info("📤 Sent session_started message to client (after session.created)")
                            except Exception as e:
                                logger.error(f"❌ Error sending session_started: {e}", exc_info=True)
                        
                        elif event_type == "session.updated":
                            # Trigger initial response from OpenAI to start the conversation
                            # Only do this once to avoid double greetings
                            if not getattr(self, 'initial_response_triggered', False):
                                try:
                                    # Just trigger a response, the system prompt already tells it to start
                                    response_create = {
                                        "type": "response.create",
                                        "response": {
                                            "modalities": ["audio", "text"],
                                        }
                                    }
                                    await self.openai_ws.send(json.dumps(response_create))
                                    self.initial_response_triggered = True
                                    logger.info("📤 Triggered initial response from OpenAI (after session.updated)")
                                except Exception as e:
                                    logger.error(f"❌ Error triggering initial response: {e}", exc_info=True)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Failed to parse OpenAI message: {e}")
                except Exception as e:
                    logger.error(f"❌ Error processing OpenAI message: {e}", exc_info=True)
                    
        except Exception as e:
            # Check if it's a ConnectionClosed error
            if websockets and isinstance(e, websockets.exceptions.ConnectionClosed):
                logger.info("OpenAI Realtime WebSocket connection closed")
                await self.send(text_data=json.dumps({
                    "type": "connection_closed",
                    "message": "Connection to OpenAI closed"
                }))
            elif isinstance(e, asyncio.CancelledError):
                logger.info("OpenAI receive task cancelled")
            else:
                logger.error(f"❌ Error receiving from OpenAI: {e}", exc_info=True)
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": f"Error receiving from OpenAI: {str(e)}"
                }))
    
    async def forward_audio_to_openai(self, audio_base64):
        """Forward audio input from browser to OpenAI Realtime API."""
        try:
            if not self.openai_ws:
                logger.warning("OpenAI WebSocket not connected")
                return
            
            # Send audio input to OpenAI Realtime API
            # The audio should be PCM16 format, base64 encoded
            audio_input = {
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }
            await self.openai_ws.send(json.dumps(audio_input))
            logger.info(f"📤 Forwarded audio chunk to OpenAI ({len(audio_base64)} bytes)")
            
        except Exception as e:
            logger.error(f"❌ Error forwarding audio to OpenAI: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": f"Error forwarding audio: {str(e)}"
            }))
    
    async def trigger_response(self):
        """Trigger OpenAI to generate a response after audio input."""
        try:
            if not self.openai_ws:
                logger.warning("OpenAI WebSocket not connected")
                return
            
            # Create response request
            response_create = {
                "type": "response.create",
                "response": {
                    "modalities": ["text", "audio"],
                    "instructions": "Respond naturally to the user's input."
                }
            }
            await self.openai_ws.send(json.dumps(response_create))
            logger.debug("📤 Triggered response generation")
            
        except Exception as e:
            logger.error(f"❌ Error triggering response: {e}", exc_info=True)
    
    async def stop_session(self):
        """Stop the interview session."""
        logger.info("🛑 Stopping session...")
        
        if self.openai_ws:
            await self.openai_ws.close()
            self.openai_ws = None
        
        if self.openai_task:
            self.openai_task.cancel()
            try:
                await self.openai_task
            except asyncio.CancelledError:
                pass
            self.openai_task = None
        
        await self.send(text_data=json.dumps({
            "type": "session_ended",
            "message": "Interview session ended"
        }))
