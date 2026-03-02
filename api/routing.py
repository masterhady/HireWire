"""
WebSocket URL routing for Django Channels.
"""

from django.urls import path
# Use the OpenAI realtime consumer implementation for realtime interview endpoints.
from api.openai_realtime_consumer import OpenAIRealtimeInterviewConsumer


websocket_urlpatterns = [
    # Backward-compatible route
    path('ws/realtime-interview/', OpenAIRealtimeInterviewConsumer.as_asgi()),
    # Explicit OpenAI realtime route
    path('ws/openai-realtime-interview/', OpenAIRealtimeInterviewConsumer.as_asgi()),
]
