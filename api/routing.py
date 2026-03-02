"""
WebSocket URL routing for Django Channels.
"""

from django.urls import path
from api.consumers import RealtimeInterviewConsumer
from api.openai_realtime_consumer import OpenAIRealtimeInterviewConsumer

websocket_urlpatterns = [
    path('ws/realtime-interview/', RealtimeInterviewConsumer.as_asgi()),
    path('ws/openai-realtime-interview/', OpenAIRealtimeInterviewConsumer.as_asgi()),
]
