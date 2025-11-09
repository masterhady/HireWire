import uuid
from django.db import models
from django.conf import settings


class SbCompany(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()
    website = models.TextField(blank=True, null=True)
    location = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "companies"


class SbUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.TextField()
    company = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING, db_column="company_id", blank=True, null=True)
    full_name = models.TextField()
    email = models.TextField(unique=False)
    password_hash = models.TextField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "users"


class Skill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()

    class Meta:
        managed = False
        db_table = "skills"


class CV(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(SbUser, models.DO_NOTHING, db_column="user_id")
    filename = models.TextField()
    parsed_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "cvs"


class CVEmbedding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cv = models.ForeignKey(CV, models.DO_NOTHING, db_column="cv_id")
    created_at = models.DateTimeField()
    # pgvector(1536) - represent as text/json for read-only purposes
    embedding = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "cv_embeddings"


class Job(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        models.DO_NOTHING,
        db_column="company_id",
        related_name="company_jobs",
    )
    title = models.TextField()
    description = models.TextField(blank=True, null=True)
    requirements = models.TextField(blank=True, null=True)
    responsibilities = models.TextField(blank=True, null=True)
    employment_type = models.TextField(blank=True, null=True)
    salary_range = models.TextField(blank=True, null=True)
    posted_at = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField()
    posted_by = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "jobs"


class JobEmbedding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, models.DO_NOTHING, db_column="job_id")
    created_at = models.DateTimeField()
    embedding = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "job_embeddings"


class Application(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cv = models.ForeignKey(CV, models.DO_NOTHING, db_column="cv_id")
    job = models.ForeignKey(Job, models.DO_NOTHING, db_column="job_id")
    company = models.ForeignKey(SbCompany, models.DO_NOTHING, db_column="company_id")
    match_score = models.DecimalField(max_digits=7, decimal_places=4, blank=True, null=True)
    matched_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "applications"


# Application Tracking Models (Django-managed for new features)
class ApplicationStatus(models.Model):
    """Tracks application status changes"""
    STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('viewed', 'Viewed'),
        ('screening', 'Screening'),
        ('interview', 'Interview'),
        ('interviewing', 'Interviewing'),
        ('offer', 'Offer'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
        ('accepted', 'Accepted'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, models.DO_NOTHING, db_column="application_id", related_name="statuses")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "application_statuses"
        ordering = ['-created_at']
        get_latest_by = 'created_at'


class ApplicationNote(models.Model):
    """Stores notes for applications"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, models.DO_NOTHING, db_column="application_id", related_name="notes")
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "application_notes"
        ordering = ['-created_at']


class Recommendation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, models.DO_NOTHING, db_column="application_id")
    section = models.TextField()
    recommendation_text = models.TextField()
    suggested_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "recommendations"


# job_skills has a composite primary key (job_id, skill_id). Django does not support composite PKs in ORM.
# We will interact with it via raw SQL in views.


class InterviewSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(SbUser, models.DO_NOTHING, db_column="user_id")
    job_description = models.TextField()
    difficulty = models.CharField(max_length=20, default="medium")
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "interview_sessions"


class InterviewQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(InterviewSession, models.DO_NOTHING, db_column="session_id")
    question = models.TextField()
    category = models.CharField(max_length=50)
    difficulty = models.CharField(max_length=20)
    tips = models.TextField(blank=True, null=True)
    expected_answer_focus = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "interview_questions"


class InterviewAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(InterviewQuestion, models.DO_NOTHING, db_column="question_id")
    user_answer = models.TextField()
    submitted_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "interview_answers"


class InterviewEvaluation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    answer = models.ForeignKey(InterviewAnswer, models.DO_NOTHING, db_column="answer_id")
    overall_score = models.IntegerField()
    strengths = models.JSONField(blank=True, null=True)
    weaknesses = models.JSONField(blank=True, null=True)
    correct_answer = models.TextField(blank=True, null=True)
    answer_analysis = models.TextField(blank=True, null=True)
    improvement_tips = models.JSONField(blank=True, null=True)
    follow_up_questions = models.JSONField(blank=True, null=True)
    evaluated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "interview_evaluations"
class AudioInterviewSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(SbUser, models.DO_NOTHING, db_column="user_id")
    job_description = models.TextField()
    difficulty = models.CharField(max_length=20, default="medium")
    voice_id = models.CharField(max_length=100, blank=True, null=True)  # For TTS voice selection
    language = models.CharField(max_length=10, default="en")
    created_at = models.DateTimeField()
    
    class Meta:
        managed = False
        db_table = "audio_interview_sessions"


class AudioInterviewQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(AudioInterviewSession, models.DO_NOTHING, db_column="session_id")
    question = models.TextField()
    category = models.CharField(max_length=50, blank=True, null=True)
    difficulty = models.CharField(max_length=20, blank=True, null=True)
    tips = models.TextField(blank=True, null=True)
    expected_answer_focus = models.TextField(blank=True, null=True)
    audio_file_path = models.CharField(max_length=500, blank=True, null=True)  # Path to TTS audio
    audio_duration = models.FloatField(blank=True, null=True)  # Duration in seconds
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "audio_interview_questions"


class AudioInterviewAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(AudioInterviewQuestion, models.DO_NOTHING, db_column="question_id")
    audio_file_path = models.CharField(max_length=500)  # Path to recorded audio
    transcribed_text = models.TextField(blank=True, null=True)  # STT result
    audio_duration = models.FloatField(blank=True, null=True)  # Duration in seconds
    transcription_confidence = models.FloatField(blank=True, null=True)  # STT confidence score
    submitted_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "audio_interview_answers"


class AudioInterviewEvaluation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    answer = models.ForeignKey(AudioInterviewAnswer, models.DO_NOTHING, db_column="answer_id")
    overall_score = models.IntegerField()
    strengths = models.JSONField(blank=True, null=True)
    weaknesses = models.JSONField(blank=True, null=True)
    correct_answer = models.TextField(blank=True, null=True)
    answer_analysis = models.TextField(blank=True, null=True)
    improvement_tips = models.JSONField(blank=True, null=True)
    follow_up_questions = models.JSONField(blank=True, null=True)
    audio_feedback_path = models.CharField(max_length=500, blank=True, null=True)  # TTS feedback
    evaluated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "audio_interview_evaluations"
