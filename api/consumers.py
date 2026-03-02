"""Compatibility wrapper for WebSocket interview consumers.

This module provides RealtimeInterviewConsumer as a compatible alias that
points to the more feature-complete OpenAI realtime consumer implementation
found in `api.openai_realtime_consumer`. Keeping this small wrapper lets
other modules continue importing `RealtimeInterviewConsumer` from
`api.consumers` while we centralize the realtime logic in a single file.
"""

from api.openai_realtime_consumer import OpenAIRealtimeInterviewConsumer

# Expose a backward-compatible name used across the codebase
RealtimeInterviewConsumer = OpenAIRealtimeInterviewConsumer

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
=======
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
>>>>>>> cad8c1536560a782f1aa7792d7fc9a59347a1680
