"""
WebSocket URL routing for Django Channels.
"""

from django.urls import path
from api.consumers import RealtimeInterviewConsumer

websocket_urlpatterns = [
    path('ws/realtime-interview/', RealtimeInterviewConsumer.as_asgi()),
]
