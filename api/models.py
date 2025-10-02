from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "admin", "Admin"
        COMPANY = "company", "Company"
        JOBSEEKER = "jobseeker", "Job Seeker"

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.JOBSEEKER,
    )
