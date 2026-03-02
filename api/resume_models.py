from django.db import models
from django.conf import settings
import uuid

class Resume(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resumes")
    title = models.CharField(max_length=255, default="My Resume")
    full_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    summary = models.TextField(blank=True)
    linkedin_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "resumes"
        ordering = ['-updated_at']

class WorkExperience(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="work_experience")
    job_title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "resume_work_experience"
        ordering = ['-start_date']

class Education(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="education")
    degree = models.CharField(max_length=255)
    institution = models.CharField(max_length=255)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "resume_education"
        ordering = ['-start_date']

class ResumeSkill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=50, blank=True) # e.g., Beginner, Intermediate, Expert

    class Meta:
        db_table = "resume_skills"

class ResumeProject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)

    class Meta:
        db_table = "resume_projects"
