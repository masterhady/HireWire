from rest_framework import serializers
from .video_interview_models import VideoInterview, VisualAnalysis

class VisualAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisualAnalysis
        fields = ['id', 'timestamp_ms', 'smile_score', 'eye_contact_score', 'posture_score', 'nervousness_score', 'dominant_expression']

class VideoInterviewSerializer(serializers.ModelSerializer):
    visual_analyses = VisualAnalysisSerializer(many=True, read_only=True)

    class Meta:
        model = VideoInterview
        fields = ['id', 'user', 'title', 'created_at', 'duration_seconds', 'overall_score', 'feedback_summary', 'visual_analyses', 'interview_type', 'topic', 'questions']
        read_only_fields = ['user', 'created_at', 'overall_score', 'feedback_summary', 'questions']

class VideoInterviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoInterview
        fields = ['title', 'interview_type', 'topic']

class VisualAnalysisCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisualAnalysis
        fields = ['timestamp_ms', 'smile_score', 'eye_contact_score', 'posture_score', 'nervousness_score', 'dominant_expression']
