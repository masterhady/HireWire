from django.db import models
from django.conf import settings
import uuid

class VideoInterview(models.Model):
    """
    Stores metadata for a video interview session.
    Note: The actual video is NOT stored, only the analysis results.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='video_interviews')
    title = models.CharField(max_length=255, default="Mock Interview")
    created_at = models.DateTimeField(auto_now_add=True)
    duration_seconds = models.IntegerField(default=0)
    overall_score = models.IntegerField(default=0) # 0-100
    feedback_summary = models.TextField(blank=True, null=True)
    
    # New fields for Question Generation
    INTERVIEW_TYPES = [('HR', 'HR'), ('Technical', 'Technical')]
    interview_type = models.CharField(max_length=20, choices=INTERVIEW_TYPES, default='HR')
    topic = models.CharField(max_length=100, blank=True, null=True)
    questions = models.JSONField(default=list, blank=True) # Stores list of generated questions

    def __str__(self):
        return f"{self.title} - {self.user.email} ({self.created_at})"

class VisualAnalysis(models.Model):
    """
    Stores the visual analysis metrics for a specific timestamp in the interview.
    """
    interview = models.ForeignKey(VideoInterview, on_delete=models.CASCADE, related_name='visual_analyses')
    timestamp_ms = models.IntegerField() # Timestamp in milliseconds from start
    
    # Metrics (0-100 or probability)
    smile_score = models.FloatField(default=0.0)
    eye_contact_score = models.FloatField(default=0.0)
    posture_score = models.FloatField(default=0.0)
    nervousness_score = models.FloatField(default=0.0)
    
    # Detected expressions (e.g., "Happy", "Neutral", "Surprised")
    dominant_expression = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['timestamp_ms']

    def __str__(self):
        return f"Analysis at {self.timestamp_ms}ms for {self.interview.id}"
