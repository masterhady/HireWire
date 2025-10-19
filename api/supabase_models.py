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
    posted_at = models.DateTimeField()
    is_active = models.BooleanField()

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